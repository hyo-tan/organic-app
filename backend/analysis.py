"""
スペクトル解析 API (Phase 3)

- POST /api/analysis/parse   : xlsx / csv をアップロードして系列データ (x, y) を返す
- POST /api/analysis/peaks   : 系列データからピークを検出する (scipy.signal.find_peaks)
- POST /api/analysis/compare : 検出ピークと DB のピークリストを照合し、候補化合物をランク付けする

DB 側のピークは compounds の peaks テーブル（キュレーション済みデータ）を使う。
IR の透過率スペクトル（下向きピーク）は invert=true で反転して検出する。
"""
from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

MAX_POINTS = 6000  # 描画用に間引く上限（ピーク検出は元データで行う想定で、必要ならクライアントが全点を送る）

# IR はバンドが広く、DB 側に範囲表記（中点で代表）も含まれるため広めに取る
TOLERANCES = {"ir": 25.0, "ei_ms": 0.6, "h_nmr": 0.15, "c_nmr": 0.6}
PEAK_KIND_BY_TYPE = {"ir": "ir", "ei_ms": "ei_ms", "h_nmr": "h_nmr", "c_nmr": "c_nmr"}


def _downsample(x: list[float], y: list[float], cap: int = MAX_POINTS) -> tuple[list[float], list[float]]:
    n = len(x)
    if n <= cap:
        return x, y
    step = n / cap
    idx = sorted({int(i * step) for i in range(cap)} | {n - 1})
    return [x[i] for i in idx], [y[i] for i in idx]


def _numeric_series(rows: list[tuple[Any, Any]], name: str) -> Optional[dict[str, Any]]:
    xs, ys = [], []
    for a, b in rows:
        try:
            xs.append(float(a))
            ys.append(float(b))
        except (TypeError, ValueError):
            continue  # ヘッダ行などは読み飛ばす
    if len(xs) < 3:
        return None
    xs, ys = _downsample(xs, ys)
    return {"name": name, "x": xs, "y": ys, "points": len(xs)}


def _parse_xlsx(content: bytes, filename: str) -> list[dict[str, Any]]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    series = []
    for ws in wb.worksheets:
        rows = [(r[0], r[1]) for r in ws.iter_rows(values_only=True) if r and len(r) >= 2]
        s = _numeric_series(rows, f"{filename} / {ws.title}")
        if s:
            series.append(s)
    return series


def _parse_csv(content: bytes, filename: str) -> list[dict[str, Any]]:
    for enc in ("utf-8-sig", "cp932"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(status_code=400, detail="CSV の文字コードを解釈できません")
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 2:
            rows.append((row[0], row[1]))
    s = _numeric_series(rows, filename)
    return [s] if s else []


@router.post("/parse")
async def parse_file(file: UploadFile = File(...)):
    content = await file.read()
    name = file.filename or "data"
    lower = name.lower()
    if lower.endswith(".xlsx"):
        series = _parse_xlsx(content, name)
    elif lower.endswith(".csv") or lower.endswith(".txt"):
        series = _parse_csv(content, name)
    else:
        raise HTTPException(status_code=400, detail="対応形式は .xlsx / .csv です")
    if not series:
        series = []
    return {"filename": name, "series": series}


class PeaksIn(BaseModel):
    x: list[float]
    y: list[float]
    invert: bool = False
    min_prominence_ratio: float = 0.05
    min_distance: int = 5


@router.post("/peaks")
def detect_peaks(body: PeaksIn):
    import numpy as np
    from scipy.signal import find_peaks

    y = np.asarray(body.y, dtype=float)
    x = np.asarray(body.x, dtype=float)
    if len(y) < 3:
        return {"peaks": []}
    sig = -y if body.invert else y
    rng = float(sig.max() - sig.min())
    if rng <= 0:
        return {"peaks": []}
    idx, props = find_peaks(sig, prominence=rng * body.min_prominence_ratio, distance=max(1, body.min_distance))
    peaks = [
        {"x": float(x[i]), "y": float(y[i]), "prominence": float(p)}
        for i, p in zip(idx, props["prominences"])
    ]
    peaks.sort(key=lambda p: p["x"])
    return {"peaks": peaks}


_NUM_RE = re.compile(r"(\d+(?:\.\d+)?)")


def _peak_center(value: Any) -> Optional[float]:
    """'3200-3600 cm⁻¹' のような範囲表記は中点、'2970 cm⁻¹' はその値を返す。"""
    if isinstance(value, (int, float)):
        return float(value)
    if not value:
        return None
    nums = [float(m) for m in _NUM_RE.findall(str(value))]
    if not nums:
        return None
    return sum(nums) / len(nums) if len(nums) > 1 else nums[0]


def _db_peaks_for(kind: str) -> list[dict[str, Any]]:
    """化合物ごとの DB ピーク位置リストを返す。"""
    import db as dblayer

    con = dblayer.connect()
    try:
        rows = con.execute(
            """SELECT p.compound_id, p.data, c.name_ja, c.name_en, c.cas, c.formula
               FROM peaks p JOIN compounds c ON c.id = p.compound_id
               WHERE p.kind=? AND c.tier='curated'""",
            (kind,),
        ).fetchall()
    finally:
        con.close()
    out = []
    for r in rows:
        try:
            plist = json.loads(r["data"]) or []
        except json.JSONDecodeError:
            continue
        peaks = []
        for p in plist:
            if kind == "ir":
                center = _peak_center(p.get("wavenumber"))
            elif kind == "ei_ms":
                center = _peak_center(p.get("mz"))
            else:
                center = _peak_center(p.get("shift"))
            if center is not None:
                peaks.append({"value": center, "assignment": p.get("assignment", ""), "raw": p})
        if peaks:
            out.append(
                {
                    "name_ja": r["name_ja"],
                    "name_en": r["name_en"],
                    "cas": r["cas"],
                    "formula": r["formula"],
                    "peaks": peaks,
                }
            )
    return out


class CompareIn(BaseModel):
    spectrum_type: str  # ir | ei_ms | h_nmr | c_nmr
    peaks_x: list[float]
    limit: int = 10


@router.post("/compare")
def compare(body: CompareIn):
    if body.spectrum_type not in TOLERANCES:
        raise HTTPException(status_code=400, detail="spectrum_type は ir / ei_ms / h_nmr / c_nmr のいずれか")
    tol = TOLERANCES[body.spectrum_type]
    kind = PEAK_KIND_BY_TYPE[body.spectrum_type]
    observed = sorted(body.peaks_x)

    results = []
    for comp in _db_peaks_for(kind):
        matched, missing = [], []
        for pk in comp["peaks"]:
            hit = next((o for o in observed if abs(o - pk["value"]) <= tol), None)
            entry = {"db_value": pk["value"], "assignment": pk["assignment"], "observed": hit}
            (matched if hit is not None else missing).append(entry)
        if not matched:
            continue
        score = len(matched) / len(comp["peaks"])
        results.append(
            {
                "name_ja": comp["name_ja"],
                "name_en": comp["name_en"],
                "cas": comp["cas"],
                "formula": comp["formula"],
                "score": round(score, 3),
                "matched": matched,
                "missing": missing,
                "total_db_peaks": len(comp["peaks"]),
            }
        )
    results.sort(key=lambda r: (-r["score"], -len(r["matched"]), r["name_en"] or ""))
    return {"tolerance": tol, "candidates": results[: max(1, min(body.limit, 50))]}
