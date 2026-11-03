"""
化合物を既存カテゴリへ自動分類するスクリプト

category が未設定（NULL）の化合物を、構造（RDKit）と英語名キーワードで
既存の14カテゴリに振り分ける。優先順位は curated 200件の分類例に合わせてある:
天然物キーワード > 含硫黄・含リン > カルボン酸 > エステル > アミド・環内窒素
> アルデヒド > ケトン > 芳香族 > ハロゲン > その他の窒素 > アルコール
> エーテル > 不飽和炭化水素 > 炭化水素 > その他

SMILES が無い PubChem 由来分は、先に PubChem から CanonicalSMILES を取得して
smiles 列も補完する。分類した行には category_auto=1 の印を付ける。
既存の category は上書きしない。再実行しても安全。

使い方:
    python classify_categories.py            # 分析のみ（DBは変更しない）
    python classify_categories.py --apply    # DBに反映する
"""
from __future__ import annotations

import argparse
import re
import time

import requests

import db as dblayer

PUBCHEM_PROP = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids}/property/SMILES,ConnectivitySMILES/JSON"

# ---------------------------------------------------------------------------
# 天然物・生体関連のキーワード（英語名の小文字に対する部分一致。
# urea だけは thiourea 等と区別するため語境界で判定する）
# ---------------------------------------------------------------------------
NATURAL_KEYWORDS = [
    # 糖
    "glucose", "fructose", "sucrose", "lactose", "maltose", "galactose",
    "ribose", "deoxyribose", "xylose", "arabinose", "rhamnose", "fucose",
    "mannose", "cellobiose", "trehalose", "sorbose", "tagatose", "psicose",
    "allose", "altrose", "gulose", "idose", "talose", "lyxose", "ribulose",
    "xylulose", "erythrose", "threose", "glyceraldehyde", "lactulose",
    "melibiose", "raffinose", "stachyose", "inulin", "sorbitol", "mannitol",
    "xylitol", "erythritol", "inositol", "glucosamine", "galactosamine",
    # 核酸塩基・ヌクレオシド
    "adenine", "guanine", "cytosine", "thymine", "uracil", "xanthine",
    "hypoxanthine", "adenosine", "guanosine", "cytidine", "uridine",
    "thymidine", "inosine", "purine", "pyrimidine",
    # アミノ酸
    "glycine", "alanine", "valine", "leucine", "isoleucine", "serine",
    "threonine", "cysteine", "cystine", "methionine", "proline",
    "phenylalanine", "tyrosine", "tryptophan", "aspartic", "glutamic",
    "asparagine", "glutamine", "lysine", "arginine", "histidine",
    "hydroxyproline", "ornithine", "citrulline", "taurine", "sarcosine",
    # テルペン・ステロイド・脂質（カンファーは curated でケトン分類のため除く）
    "menthol", "limonene", "pinene", "citral", "borneol",
    "carvone", "geraniol", "linalool", "citronellol", "farnesol",
    "squalene", "retinol", "cholesterol", "ergosterol", "stigmasterol",
    "sitosterol", "testosterone", "estradiol", "estriol", "estrone",
    "progesterone", "cortisol", "cortisone", "aldosterone",
    "prostaglandin", "thromboxane", "leukotriene", "cholic", "bile",
    "carotene", "lycopene", "lutein", "zeaxanthin", "chlorophyll",
    # アルカロイド・その他生体分子
    "caffeine", "nicotine", "morphine", "codeine", "cocaine", "atropine",
    "quinine", "quinidine", "strychnine", "ephedrine", "theobromine",
    "berberine", "papaverine", "scopolamine", "vanillin", "eugenol",
    "capsaicin", "curcumin", "carnitine", "choline", "betaine", "creatine",
    "creatinine", "heme", "bilirubin", "biliverdin", "vitamin",
]

CATEGORIES = [
    "天然物・生体関連", "含硫黄・含リン化合物", "カルボン酸", "エステル",
    "アミン・窒素化合物", "アルデヒド", "ケトン", "芳香族",
    "ハロゲン化物・溶媒", "アルコール", "エーテル", "不飽和炭化水素",
    "炭化水素", "その他",
]


def is_natural(name_en: str | None, name_ja: str | None) -> bool:
    text = f"{name_en or ''}".lower()
    if re.search(r"\burea\b", text):
        return True
    if re.search(r"\b\w+ose\b", text):  # 糖の -ose 語尾
        return True
    return any(k in text for k in NATURAL_KEYWORDS)


def classify(smiles: str | None, name_en: str | None, name_ja: str | None, formula: str | None) -> str:
    from rdkit import Chem
    from rdkit.Chem import Descriptors  # noqa: F401  (rdkit import check)

    if is_natural(name_en, name_ja):
        return "天然物・生体関連"

    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return classify_by_name(name_en, formula)

    atoms = mol.GetAtoms()
    symbols = [a.GetSymbol() for a in atoms]
    if any(s in ("S", "P") for s in symbols):
        return "含硫黄・含リン化合物"

    def has_smarts(pat: str) -> bool:
        q = Chem.MolFromSmarts(pat)
        return q is not None and mol.HasSubstructMatch(q)

    # カルボン酸（カルボキシ基・カルボン酸塩・酸ハロゲン化物）
    if has_smarts("[CX3](=O)[OX2H1]") or has_smarts("[CX3](=O)[O-]") or has_smarts("[CX3](=O)[Cl,Br,F,I]"):
        return "カルボン酸"
    # エステル（ラクトン・炭酸エステル・無水物を含む）
    if has_smarts("[CX3](=O)[OX2][#6]"):
        return "エステル"
    # アミド、または環内窒素（ピリジン・モルホリン等）-> アミン・窒素化合物
    ring_atoms = set()
    for ring in mol.GetRingInfo().AtomRings():
        ring_atoms.update(ring)
    if has_smarts("[CX3](=O)[NX3]") or any(
        a.GetSymbol() == "N" and a.GetIdx() in ring_atoms for a in atoms
    ):
        return "アミン・窒素化合物"
    # アルデヒド / ケトン
    if has_smarts("[CX3H1](=O)[#6]") or has_smarts("[CH2]=O"):
        return "アルデヒド"
    if has_smarts("[#6][CX3](=O)[#6]"):
        return "ケトン"
    # 芳香環より優先する2ケース（curated の分類に合わせる）:
    # アニソール型（芳香環に直結したエーテル酸素）-> エーテル、
    # ベンジルアルコール型（脂肪族OH）-> アルコール。フェノール型OHは芳香族のまま。
    for a in atoms:
        if a.GetSymbol() != "O" or a.GetDegree() != 2 or a.GetTotalNumHs() > 0:
            continue
        nbrs = [n for n in a.GetNeighbors()]
        if a.GetIdx() not in ring_atoms and any(n.GetIsAromatic() for n in nbrs):
            return "エーテル"
    for a in atoms:
        if a.GetSymbol() == "O" and a.GetTotalNumHs() >= 1:
            for n in a.GetNeighbors():
                if n.GetSymbol() == "C" and not n.GetIsAromatic():
                    return "アルコール"
    # 芳香族（全炭素の芳香環）
    for ring in mol.GetRingInfo().AtomRings():
        if all(atoms[i].GetIsAromatic() and atoms[i].GetSymbol() == "C" for i in ring):
            return "芳香族"
    # ハロゲン
    if any(s in ("F", "Cl", "Br", "I") for s in symbols):
        return "ハロゲン化物・溶媒"
    # その他の窒素
    if "N" in symbols:
        return "アミン・窒素化合物"
    # アルコール / エーテル
    if has_smarts("[OX2H1][#6]"):
        return "アルコール"
    if has_smarts("[#6][OX2H0][#6]"):
        return "エーテル"
    # 炭化水素
    if set(symbols) <= {"C", "H"}:
        if has_smarts("C=C") or has_smarts("C#C"):
            return "不飽和炭化水素"
        return "炭化水素"
    return "その他"


def classify_by_name(name_en: str | None, formula: str | None) -> str:
    """SMILES が無い場合のフォールバック（分子式と英語名から判定）。"""
    name = (name_en or "").lower()
    f = formula or ""
    if any(x in f for x in ("Cl", "Br")) or re.search(r"(^|[^a-z])F($|[^a-z])", f) or " I" in f or f.endswith("I"):
        if not any(k in name for k in ("acid", "ester")):
            return "ハロゲン化物・溶媒"
    if "S" in f or "P" in f:
        return "含硫黄・含リン化合物"
    if "oic acid" in name or "carboxylic acid" in name:
        return "カルボン酸"
    if "ate" in name or "ester" in name:
        return "エステル"
    if "amine" in name or "amide" in name or "nitrile" in name or "amino" in name:
        return "アミン・窒素化合物"
    if name.rstrip().endswith("al") or "aldehyde" in name:
        return "アルデヒド"
    if "one" in name and "N" not in f:
        return "ケトン"
    if "benzene" in name or "phenyl" in name or "naphthalene" in name or "phenol" in name:
        return "芳香族"
    if "N" in f:
        return "アミン・窒素化合物"
    if name.rstrip().endswith("ol"):
        return "アルコール"
    if "ether" in name:
        return "エーテル"
    return "その他"


def fetch_smiles(con, batch: int = 100) -> int:
    """SMILES が空の pubchem 行について PubChem から取得して埋める。"""
    rows = con.execute(
        "SELECT id, cid FROM compounds WHERE (smiles IS NULL OR smiles='') AND cid IS NOT NULL"
    ).fetchall()
    print(f"smiles fetch targets: {len(rows)}")
    filled = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        cids = ",".join(str(r["cid"]) for r in chunk)
        try:
            r = requests.get(PUBCHEM_PROP.format(cids=cids), timeout=120)
            if r.status_code != 200:
                print(f"  [warn] pubchem status {r.status_code} at {i}")
                time.sleep(5)
                continue
            props = {p["CID"]: (p.get("SMILES") or p.get("ConnectivitySMILES")) for p in r.json()["PropertyTable"]["Properties"]}
        except requests.RequestException as e:
            print(f"  [warn] pubchem error: {e}")
            time.sleep(5)
            continue
        for row in chunk:
            smi = props.get(row["cid"])
            if smi:
                con.execute("UPDATE compounds SET smiles=? WHERE id=?", (smi, row["id"]))
                filled += 1
        con.commit()
        if (i // batch) % 20 == 0:
            print(f"  {i + len(chunk)}/{len(rows)} (filled {filled})", flush=True)
        time.sleep(0.2)
    print(f"smiles filled: {filled}")
    return filled


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-fetch", action="store_true", help="SMILES取得をスキップ")
    args = ap.parse_args()

    con = dblayer.connect()
    try:
        if not args.no_fetch:
            fetch_smiles(con)

        rows = con.execute(
            "SELECT id, name_en, name_ja, formula, smiles, tier FROM compounds WHERE category IS NULL"
        ).fetchall()
        print(f"classify targets: {len(rows)}")

        from collections import Counter

        dist = Counter()
        samples: dict[str, list[str]] = {}
        assignments: list[tuple[int, str]] = []
        for row in rows:
            cat = classify(row["smiles"], row["name_en"], row["name_ja"], row["formula"])
            dist[cat] += 1
            assignments.append((row["id"], cat))
            if len(samples.setdefault(cat, [])) < 5:
                samples[cat].append(row["name_ja"] or row["name_en"] or "?")

        for cat in CATEGORIES:
            print(f"  {cat}: {dist.get(cat, 0)}")
            for s in samples.get(cat, []):
                print(f"      - {s}")

        if args.apply:
            cols = [r[1] for r in con.execute("PRAGMA table_info(compounds)").fetchall()]
            if "category_auto" not in cols:
                con.execute("ALTER TABLE compounds ADD COLUMN category_auto INTEGER DEFAULT 0")
            for cid_, cat in assignments:
                con.execute(
                    "UPDATE compounds SET category=?, category_auto=1 WHERE id=? AND category IS NULL",
                    (cat, cid_),
                )
            con.commit()
            print("applied.")
            for cat, n in con.execute("SELECT category, COUNT(*) FROM compounds GROUP BY category ORDER BY COUNT(*) DESC"):
                print(f"  total {cat}: {n}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
