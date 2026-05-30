import json
import time
from pathlib import Path

import requests

from compound_catalog import build_compound_catalog
from category_rules import detect_category
from peak_templates import generate_ir, generate_ms, generate_h_nmr, generate_c_nmr

BASE_DIR = Path(__file__).parent

IMPORTANT_PATH = BASE_DIR / "important_compounds.json"
OUTPUT_PATH = BASE_DIR / "compounds.json"

TARGET_TOTAL = 200

PUBCHEM_PROPERTIES = (
    "SMILES,"
    "CanonicalSMILES,"
    "IsomericSMILES,"
    "ConnectivitySMILES,"
    "MolecularFormula,"
    "MolecularWeight,"
    "IUPACName"
)


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def pick_smiles(prop: dict) -> str:
    return (
        prop.get("SMILES")
        or prop.get("CanonicalSMILES")
        or prop.get("ConnectivitySMILES")
        or prop.get("IsomericSMILES")
        or ""
    )


def load_json(path, default):
    if not path.exists():
        return default

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_pubchem(name, max_retries=3):
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{name}/property/{PUBCHEM_PROPERTIES}/JSON"
    )

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  PubChem問い合わせ {attempt}/{max_retries}: {name}")

            res = requests.get(url, timeout=20)

            if res.status_code == 200:
                data = res.json()
                prop = data["PropertyTable"]["Properties"][0]

                smiles = pick_smiles(prop)

                return {
                    "cid": prop.get("CID"),
                    "formula": prop.get("MolecularFormula", ""),
                    "mw": float(prop.get("MolecularWeight", 0)),
                    "smiles": smiles,
                    "iupac_name": prop.get("IUPACName", name),
                }

            print(f"  PubChem取得失敗: {name} / status={res.status_code}")

        except Exception as e:
            print(f"  PubChem取得エラー: {name} / attempt={attempt} / {e}")

        time.sleep(2.0 * attempt)

    return None


def make_auto_compound(item):
    name_en = item["name_en"]
    name_ja = item["name_ja"]

    pubchem = fetch_pubchem(name_en)

    if not pubchem:
        return None

    smiles = pubchem["smiles"]
    mw = pubchem["mw"]
    iupac_name = pubchem["iupac_name"]

    compound = {
        "name_ja": name_ja,
        "name_en": name_en,
        "iupac_name": iupac_name,
        "cas": f"auto-{name_en}",
        "cid": pubchem["cid"],
        "formula": pubchem["formula"],
        "mw": mw,
        "smiles": smiles,
        "melting_point": "-",
        "boiling_point": "-",
        "density": "-",
        "state": "unknown",
        "data_quality": "generated",
        "ir_peaks": generate_ir(smiles),
        "ei_ms_peaks": generate_ms(mw, smiles),
        "h_nmr_peaks": generate_h_nmr(smiles),
        "c_nmr_peaks": generate_c_nmr(smiles),
    }

    compound["category"] = detect_category(compound)

    return compound


def main():
    important = load_json(IMPORTANT_PATH, [])
    catalog = build_compound_catalog()

    print(f"important_compounds 件数: {len(important)}")
    print(f"候補カタログ件数: {len(catalog)}")
    print(f"目標合計件数: {TARGET_TOTAL}")

    compounds = []

    # 既存の高品質データを先に入れる
    for compound in important:
        compound["data_quality"] = compound.get("data_quality", "high")
        compound["category"] = detect_category(compound)
        compounds.append(compound)

    existing_names = {
        normalize(c.get("name_en") or c.get("name_ja") or "")
        for c in compounds
    }

    generated_count = 0
    skipped_count = 0
    no_smiles_count = 0

    for index, item in enumerate(catalog, start=1):
        if len(compounds) >= TARGET_TOTAL:
            break

        name_en = item["name_en"]

        if normalize(name_en) in existing_names:
            skipped_count += 1
            continue

        print(f"[{index}/{len(catalog)}] 取得中: {item['name_ja']} / {name_en}")

        compound = make_auto_compound(item)

        if compound is None:
            skipped_count += 1
            continue

        if not compound.get("smiles"):
            print(f"  注意: SMILESが空です: {name_en}")
            no_smiles_count += 1

        compounds.append(compound)
        existing_names.add(normalize(name_en))
        generated_count += 1

        # PubChemに連続アクセスしすぎない
        time.sleep(1.0)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(compounds, f, ensure_ascii=False, indent=2)

    print("----------")
    print(f"重点化合物: {len(important)} 件")
    print(f"自動生成: {generated_count} 件")
    print(f"スキップ/取得失敗: {skipped_count} 件")
    print(f"SMILES空: {no_smiles_count} 件")
    print(f"合計: {len(compounds)} 件")
    print(f"保存先: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()