"""
SQLite データ層 (Phase 1: DB化)

compounds.json / spectra/*.json の代わりに SQLite を正本にするためのモジュール。
- compounds: 化合物本体（キュレーション済み tier='curated' と PubChem 拡張 tier='pubchem'）
- peaks:      ピークリスト（IR / EI-MS / H-NMR / C-NMR）を JSON 文字列で保持
- spectra:    スペクトル曲線データ。JSON を zlib 圧縮した BLOB で保持（容量を約1/10に削減）
- synonyms:   別名（検索用）

FastAPI 側は load_compounds() / get_spectrum_data() 経由で従来と同じ dict 形状を受け取る。
"""
from __future__ import annotations

import json
import sqlite3
import zlib
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "compounds.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS compounds(
  id INTEGER PRIMARY KEY,
  cid INTEGER,
  cas TEXT UNIQUE,
  name_ja TEXT,
  name_en TEXT,
  iupac_name TEXT,
  formula TEXT,
  mw REAL,
  smiles TEXT,
  inchi_key TEXT UNIQUE,
  melting_point TEXT,
  boiling_point TEXT,
  density TEXT,
  state TEXT,
  category TEXT,
  data_quality TEXT,
  tier TEXT DEFAULT 'pubchem',
  synonyms TEXT DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_c_name_ja ON compounds(name_ja);
CREATE INDEX IF NOT EXISTS idx_c_name_en ON compounds(name_en);
CREATE INDEX IF NOT EXISTS idx_c_formula ON compounds(formula);
CREATE INDEX IF NOT EXISTS idx_c_cid ON compounds(cid);
CREATE TABLE IF NOT EXISTS peaks(
  compound_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  data TEXT,
  PRIMARY KEY(compound_id, kind)
);
CREATE TABLE IF NOT EXISTS spectra(
  compound_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  source TEXT,
  x_unit TEXT,
  y_unit TEXT,
  data_z BLOB,
  PRIMARY KEY(compound_id, kind)
);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS stage_b_done(cid INTEGER PRIMARY KEY, done_at TEXT);
"""

PEAK_KEYS = {"ir": "ir_peaks", "ei_ms": "ei_ms_peaks", "h_nmr": "h_nmr_peaks", "c_nmr": "c_nmr_peaks"}
SPECTRA_KINDS = ("ir", "ei_ms", "h_nmr", "c_nmr")

COMPOUND_COLUMNS = (
    "cid", "cas", "name_ja", "name_en", "iupac_name", "formula", "mw", "smiles",
    "inchi_key", "melting_point", "boiling_point", "density", "state",
    "category", "data_quality", "tier", "synonyms",
)


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(db_path or DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def upsert_compound(con: sqlite3.Connection, c: dict[str, Any]) -> int:
    """化合物を1件登録/更新し、id を返す。重複判定は inchi_key → cas → cid の順。"""
    values = {k: c.get(k) for k in COMPOUND_COLUMNS}
    if isinstance(values.get("synonyms"), (list, tuple)):
        values["synonyms"] = json.dumps(list(values["synonyms"]), ensure_ascii=False)

    row = None
    if values.get("inchi_key"):
        row = con.execute("SELECT * FROM compounds WHERE inchi_key=?", (values["inchi_key"],)).fetchone()
    if row is None and values.get("cas"):
        row = con.execute("SELECT * FROM compounds WHERE cas=?", (values["cas"],)).fetchone()
    if row is None and values.get("cid"):
        row = con.execute("SELECT * FROM compounds WHERE cid=?", (values["cid"],)).fetchone()

    if row:
        cid_id = row["id"]
        if row["tier"] == "curated":
            # キュレーション済みデータは正本。PubChem 側の値では上書きせず、
            # 空いている項目 (cid, synonyms など) だけを補完する。
            fills = {
                k: v
                for k, v in values.items()
                if v not in (None, "", "[]") and row[k] in (None, "", "[]")
            }
            if fills:
                sets = ", ".join(f"{k}=?" for k in fills)
                con.execute(f"UPDATE compounds SET {sets} WHERE id=?", (*fills.values(), cid_id))
            return cid_id
        sets = ", ".join(f"{k}=?" for k in COMPOUND_COLUMNS)
        con.execute(f"UPDATE compounds SET {sets} WHERE id=?", (*values.values(), cid_id))
        return cid_id

    cols = ", ".join(COMPOUND_COLUMNS)
    ph = ", ".join("?" for _ in COMPOUND_COLUMNS)
    cur = con.execute(f"INSERT INTO compounds({cols}) VALUES({ph})", tuple(values.values()))
    return int(cur.lastrowid)


def set_peaks(con: sqlite3.Connection, compound_id: int, kind: str, peaks: Any) -> None:
    if peaks:
        con.execute(
            "INSERT OR REPLACE INTO peaks VALUES(?,?,?)",
            (compound_id, kind, json.dumps(peaks, ensure_ascii=False)),
        )


def set_spectrum(con: sqlite3.Connection, compound_id: int, kind: str, spec: dict[str, Any]) -> None:
    blob = zlib.compress(json.dumps(spec.get("data", [])).encode("utf-8"), 9)
    con.execute(
        "INSERT OR REPLACE INTO spectra VALUES(?,?,?,?,?,?)",
        (compound_id, kind, spec.get("source"), spec.get("x_unit"), spec.get("y_unit"), blob),
    )


def _row_to_compound(con: sqlite3.Connection, row: sqlite3.Row, with_peaks: bool = True, spectra_kinds: Optional[list] = None) -> dict[str, Any]:
    c = {k: row[k] for k in row.keys() if k != "id"}
    try:
        c["synonyms"] = json.loads(c.get("synonyms") or "[]")
    except json.JSONDecodeError:
        c["synonyms"] = []
    if with_peaks:
        for kind, key in PEAK_KEYS.items():
            r = con.execute("SELECT data FROM peaks WHERE compound_id=? AND kind=?", (row["id"], kind)).fetchone()
            c[key] = json.loads(r["data"]) if r else []
    if spectra_kinds is None:
        spectra_kinds = [r[0] for r in con.execute("SELECT kind FROM spectra WHERE compound_id=? UNION SELECT kind FROM peaks WHERE compound_id=? ORDER BY kind", (row["id"], row["id"])).fetchall()]
    # スペクトルデータが登録されている種別（例: ["ir", "ei_ms", "h_nmr", "c_nmr"]）。
    # 曲線（spectra）だけでなくピークのみの登録も含む。
    # フロント側で「未登録」を fetch 前に判定するために付与する。
    c["spectra_kinds"] = spectra_kinds
    return c


def load_compounds(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute("SELECT * FROM compounds ORDER BY id").fetchall()
    kinds_map: dict[int, list[str]] = {}
    for compound_id, kind in con.execute("SELECT compound_id, kind FROM spectra UNION SELECT compound_id, kind FROM peaks"):
        lst = kinds_map.setdefault(compound_id, [])
        if kind not in lst:
            lst.append(kind)
    for lst in kinds_map.values():
        lst.sort()
    return [_row_to_compound(con, r, spectra_kinds=kinds_map.get(r["id"], [])) for r in rows]


def get_spectrum_data(con: sqlite3.Connection, cas: str, kind: str) -> Optional[dict[str, Any]]:
    r = con.execute(
        """SELECT s.* FROM spectra s JOIN compounds c ON c.id = s.compound_id
           WHERE c.cas=? AND s.kind=?""",
        (cas, kind),
    ).fetchone()
    if r is None:
        return None
    return {
        "type": kind.upper().replace("_", "-"),
        "source": r["source"],
        "source_url": "",
        "x_unit": r["x_unit"],
        "y_unit": r["y_unit"],
        "data": json.loads(zlib.decompress(r["data_z"])),
    }


def count_compounds(con: sqlite3.Connection) -> int:
    return int(con.execute("SELECT COUNT(*) FROM compounds").fetchone()[0])


def get_meta(con: sqlite3.Connection, key: str) -> Optional[str]:
    r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return r["value"] if r else None


def set_meta(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, value))
