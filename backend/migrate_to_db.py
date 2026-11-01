"""
既存の JSON データを SQLite (compounds.db) に移行するスクリプト (Phase 1)

使い方:
    python migrate_to_db.py [--db compounds.db]

- compounds.json の全件を tier='curated' として登録（InChIKey は RDKit で SMILES から算出）
- spectra/<CAS or auto-name>/*.json の曲線データを圧縮して取り込む
- 既存DBがある場合は作り直す（元JSONは変更しない）
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import db as dblayer

BASE_DIR = Path(__file__).parent
SPECTRA_FILEMAP = {"ir.json": "ir", "ei-ms.json": "ei_ms", "h-nmr.json": "h_nmr", "c-nmr.json": "c_nmr"}
PEAK_FILEMAP = {"ir_peaks": "ir", "ei_ms_peaks": "ei_ms", "h_nmr_peaks": "h_nmr", "c_nmr_peaks": "c_nmr"}


def inchi_key_from_smiles(smiles: str | None) -> str | None:
    if not smiles:
        return None
    try:
        from rdkit import Chem

        mol = Chem.MolFromSmiles(smiles)
        return Chem.MolToInchiKey(mol) if mol else None
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(dblayer.DB_PATH))
    args = ap.parse_args()

    db_path = Path(args.db)
    if db_path.exists():
        db_path.unlink()

    compounds = json.loads((BASE_DIR / "compounds.json").read_text(encoding="utf-8"))
    con = dblayer.connect(db_path)
    dblayer.init_db(con)

    n_spec = 0
    for c in compounds:
        row = dict(c)
        row["tier"] = "curated"
        row["inchi_key"] = row.get("inchi_key") or inchi_key_from_smiles(row.get("smiles"))
        row.setdefault("synonyms", [])
        cid_id = dblayer.upsert_compound(con, row)
        for key, kind in PEAK_FILEMAP.items():
            dblayer.set_peaks(con, cid_id, kind, c.get(key))

        folder = BASE_DIR / "spectra" / (c.get("cas") or "")
        if not folder.exists():
            folder = BASE_DIR / "spectra" / ("auto-" + (c.get("name_en") or "").lower())
        if folder.exists():
            for fname, kind in SPECTRA_FILEMAP.items():
                p = folder / fname
                if p.exists():
                    dblayer.set_spectrum(con, cid_id, kind, json.loads(p.read_text(encoding="utf-8")))
                    n_spec += 1
    con.commit()
    total = dblayer.count_compounds(con)
    print(f"migrated: {total} compounds, {n_spec} spectra -> {db_path} ({db_path.stat().st_size/1e6:.1f} MB)")
    con.close()


if __name__ == "__main__":
    main()
