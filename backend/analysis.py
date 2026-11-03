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
               WHERE p.kind=?""",
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
        if kind == "ei_ms":
            # EI-MS は取り込みデータだとピーク数が多い（最大40件）ため、
            # 照合には強度の高い上位10件だけを使う（割合スコアが不当に下がるのを防ぐ）
            plist = sorted(plist, key=lambda p: -(p.get("intensity") or 0))[:10]
        for p in plist:
            if kind == "ir":
                center = _peak_center(p.get("wavenumber"))
                inten = None
            elif kind == "ei_ms":
                center = _peak_center(p.get("mz"))
                inten = p.get("intensity") if isinstance(p.get("intensity"), (int, float)) else None
            else:
                center = _peak_center(p.get("shift"))
                # 1H NMR は積分値（"2H" など）を強度として使う。13C は強度なし
                inten = _peak_center(p.get("integration")) if kind == "h_nmr" else None
            if center is not None:
                peaks.append({"value": center, "assignment": p.get("assignment", ""), "raw": p, "intensity": inten})
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
    peaks_y: Optional[list[float]] = None  # 観測ピークの強度（任意。あれば強度もスコアに使う）
    limit: int = 10


@router.post("/compare")
def compare(body: CompareIn):
    if body.spectrum_type not in TOLERANCES:
        raise HTTPException(status_code=400, detail="spectrum_type は ir / ei_ms / h_nmr / c_nmr のいずれか")
    tol = TOLERANCES[body.spectrum_type]
    kind = PEAK_KIND_BY_TYPE[body.spectrum_type]
    # 観測ピーク（位置, 強度）。強度が無い/数が合わない場合は位置のみで照合する
    if body.peaks_y and len(body.peaks_y) == len(body.peaks_x):
        omax = max(body.peaks_y) or 1.0
        # 強度は「観測全体の最大ピーク=1」基準に正規化（DB側も化合物内の最大=1に揃える）
        obs_pairs = sorted(((x, y / omax) for x, y in zip(body.peaks_x, body.peaks_y)), key=lambda t: t[0])
    else:
        obs_pairs = [(x, None) for x in sorted(body.peaks_x)]
    intensity_kinds = kind in ("ei_ms", "h_nmr")

    results = []
    for comp in _db_peaks_for(kind):
        matched, missing = [], []
        inten_pairs = []
        db_intens = [pk["intensity"] for pk in comp["peaks"] if pk.get("intensity") is not None]
        dmax = max(db_intens) if db_intens else 1.0
        for pk in comp["peaks"]:
            cands = [o for o in obs_pairs if abs(o[0] - pk["value"]) <= tol]
            hit = min(cands, key=lambda o: abs(o[0] - pk["value"])) if cands else None
            entry = {"db_value": pk["value"], "assignment": pk["assignment"], "observed": hit[0] if hit else None}
            if hit is not None:
                matched.append(entry)
                if pk.get("intensity") is not None and hit[1] is not None and dmax > 0:
                    inten_pairs.append((float(pk["intensity"]) / dmax, float(hit[1])))
            else:
                missing.append(entry)
        if not matched:
            continue
        coverage = len(matched) / len(comp["peaks"])
        # 強度の近さ: 一致ペアの強度比（log）の平均から類似度を作る。
        # コサイン類似度は正の短いベクトルだと大抵1に近づいてしまうため、
        # 「100のはずが13しかない」のような桁違いを強く罰する方式にする
        sim = None
        log_pairs = [(a, b) for a, b in inten_pairs if a > 0 and b > 0]
        if len(log_pairs) >= 2:
            import math

            mean_log = sum(abs(math.log(a / b)) for a, b in log_pairs) / len(log_pairs)
            sim = 1.0 / (1.0 + mean_log)
        if sim is not None:
            score = coverage * (0.5 + 0.5 * sim)
        elif intensity_kinds:
            # 強度で検証できなかった候補は、強度が合った候補より少し下に置く
            score = coverage * (0.5 + 0.5 * 0.85)
        else:
            score = coverage
        results.append(
            {
                "name_ja": comp["name_ja"],
                "name_en": comp["name_en"],
                "cas": comp["cas"],
                "formula": comp["formula"],
                "score": round(score, 3),
                "coverage": round(coverage, 3),
                "intensity_similarity": round(sim, 3) if sim is not None else None,
                "matched": matched,
                "missing": missing,
                "total_db_peaks": len(comp["peaks"]),
            }
        )
    results.sort(key=lambda r: (-r["score"], -len(r["matched"]), r["name_en"] or ""))
    return {"tolerance": tol, "candidates": results[: max(1, min(body.limit, 50))]}
