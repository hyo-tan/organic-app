import json
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
COMPOUNDS_PATH = BASE_DIR / "compounds.json"

PUBCHEM_PROPERTIES = (
    "SMILES,"
    "CanonicalSMILES,"
    "IsomericSMILES,"
    "ConnectivitySMILES,"
    "IUPACName,"
    "MolecularFormula,"
    "MolecularWeight"
)


def pick_smiles(prop: dict) -> str:
    """
    PubChem の返却キー名ゆれに対応して SMILES を拾う。
    今回のヘプタンでは 'SMILES' と 'ConnectivitySMILES' が返っていたので、
    'SMILES' を最優先にする。
    """
    return (
        prop.get("SMILES")
        or prop.get("CanonicalSMILES")
        or prop.get("ConnectivitySMILES")
        or prop.get("IsomericSMILES")
        or ""
    )


def fetch_by_cid(cid):
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
        f"{cid}/property/{PUBCHEM_PROPERTIES}/JSON"
    )

    try:
        res = requests.get(url, timeout=15)

        if res.status_code != 200:
            print(f"  CID取得失敗: CID={cid}, status={res.status_code}")
            return None

        data = res.json()
        return data["PropertyTable"]["Properties"][0]

    except Exception as e:
        print(f"  CID取得エラー: CID={cid}, error={e}")
        return None


def fetch_by_name(name):
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{name}/property/{PUBCHEM_PROPERTIES}/JSON"
    )

    try:
        res = requests.get(url, timeout=15)

        if res.status_code != 200:
            print(f"  name取得失敗: name={name}, status={res.status_code}")
            return None

        data = res.json()
        return data["PropertyTable"]["Properties"][0]

    except Exception as e:
        print(f"  name取得エラー: name={name}, error={e}")
        return None


def main():
    with open(COMPOUNDS_PATH, encoding="utf-8") as f:
        compounds = json.load(f)

    fixed = 0
    already_has_smiles = 0
    failed = []

    for compound in compounds:
        current_smiles = compound.get("smiles", "")
        cid = compound.get("cid")
        name_en = compound.get("name_en", "")
        name_ja = compound.get("name_ja", "")

        if current_smiles:
            already_has_smiles += 1
            continue

        print(f"SMILES補完中: {name_ja} / {name_en} / CID={cid}")

        prop = None

        if cid:
            prop = fetch_by_cid(cid)

        if prop is None and name_en:
            prop = fetch_by_name(name_en)

        if prop is None:
            print("  -> PubChemから取得できませんでした")
            failed.append(f"{name_ja} / {name_en} / CID={cid}")
            time.sleep(0.2)
            continue

        print(f"  取得キー: {list(prop.keys())}")

        new_smiles = pick_smiles(prop)

        if new_smiles:
            compound["smiles"] = new_smiles

            if prop.get("IUPACName"):
                compound["iupac_name"] = prop.get("IUPACName")

            if prop.get("MolecularFormula"):
                compound["formula"] = prop.get("MolecularFormula")

            if prop.get("MolecularWeight"):
                try:
                    compound["mw"] = float(prop.get("MolecularWeight"))
                except ValueError:
                    compound["mw"] = prop.get("MolecularWeight")

            print(f"  -> SMILES: {new_smiles}")
            fixed += 1
        else:
            print("  -> SMILESキーが見つかりませんでした")
            failed.append(f"{name_ja} / {name_en} / CID={cid}")

        time.sleep(0.2)

    with open(COMPOUNDS_PATH, "w", encoding="utf-8") as f:
        json.dump(compounds, f, ensure_ascii=False, indent=2)

    print("----------")
    print(f"既にSMILESあり: {already_has_smiles}")
    print(f"SMILES補完数: {fixed}")

    if failed:
        print("補完失敗:")
        for item in failed:
            print(f"- {item}")

    print(f"保存先: {COMPOUNDS_PATH}")


if __name__ == "__main__":
    main()