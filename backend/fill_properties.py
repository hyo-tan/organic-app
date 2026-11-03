"""
fill_properties.py — 基本物性（融点・沸点）の補完

方針（ユーザーの選択「実験値を優先し、残りを推定値で埋める」）:
  1. Wikidata の実験値（融点 P2101 / 沸点 P2102、PubChem CID 経由）で空欄を埋める
  2. 残りは Joback 法（基団寄与法）で構造式から推定し、「（推定）」を付けて埋める
  密度は信頼できる簡易推定法がないため対象外。
  既存の値は一切上書きしない（空欄のみ補完）。

使い方:
  python fill_properties.py validate   # Joback の精度検証のみ（DB変更なし）
  python fill_properties.py wikidata   # Wikidata 実験値で補完
  python fill_properties.py joback     # Joback 推定値で補完
  python fill_properties.py all        # wikidata -> joback の順に実行
"""
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "compounds.db"

# ---------------------------------------------------------------- Wikidata
SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "OrganicAppPropertyFill/1.0 (research)"}


def fetch_wikidata_props(cids):
    """CID のリスト -> {cid: {'mp': celsius, 'bp': celsius}}
    psv の正規化量はケルビンで返るので °C に換算する。"""
    result = {}
    BATCH = 400
    for start in range(0, len(cids), BATCH):
        batch = cids[start:start + BATCH]
        values = " ".join(f'"{c}"' for c in batch)
        query = f"""
        SELECT ?cid ?mpK ?bpK WHERE {{
          VALUES ?cid {{ {values} }}
          ?item wdt:P662 ?cid .
          OPTIONAL {{ ?item p:P2101/psv:P2101 [ wikibase:quantityAmount ?mpK ] }}
          OPTIONAL {{ ?item p:P2102/psv:P2102 [ wikibase:quantityAmount ?bpK ] }}
        }}"""
        for attempt in range(3):
            try:
                r = requests.get(SPARQL_URL, params={"query": query, "format": "json"},
                                 headers=HEADERS, timeout=120)
                if r.status_code == 200:
                    for b in r.json()["results"]["bindings"]:
                        cid = int(b["cid"]["value"])
                        entry = result.setdefault(cid, {})
                        if "mpK" in b:
                            entry["mp"] = float(b["mpK"]["value"]) - 273.15
                        if "bpK" in b:
                            entry["bp"] = float(b["bpK"]["value"]) - 273.15
                    break
                time.sleep(5 * (attempt + 1))
            except Exception:
                time.sleep(5 * (attempt + 1))
        print(f"  wikidata batch {start + len(batch)}/{len(cids)} (found so far: {len(result)})")
        time.sleep(1)
    return result


def fmt_celsius(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return f"{s} °C"


def is_empty(v):
    return v is None or v == ""


def wikidata_fill(db):
    rows = db.execute(
        "SELECT id, cid FROM compounds WHERE cid IS NOT NULL "
        "AND ((melting_point IS NULL OR melting_point='') OR (boiling_point IS NULL OR boiling_point=''))"
    ).fetchall()
    print(f"wikidata targets: {len(rows)}")
    props = fetch_wikidata_props([r[1] for r in rows])
    mp_filled = bp_filled = 0
    for cid_id, cid in rows:
        p = props.get(cid)
        if not p:
            continue
        cur_mp, cur_bp = db.execute(
            "SELECT melting_point, boiling_point FROM compounds WHERE id=?", (cid_id,)).fetchone()
        if "mp" in p and is_empty(cur_mp):
            db.execute("UPDATE compounds SET melting_point=? WHERE id=?", (fmt_celsius(p["mp"]), cid_id))
            mp_filled += 1
        if "bp" in p and is_empty(cur_bp):
            db.execute("UPDATE compounds SET boiling_point=? WHERE id=?", (fmt_celsius(p["bp"]), cid_id))
            bp_filled += 1
    db.commit()
    print(f"wikidata filled: mp +{mp_filled}, bp +{bp_filled}")


# ---------------------------------------------------------------- Joback
# (ΔTb, ΔTm) — Joback & Reid の基団寄与表（Wikipedia "Joback method" の表より）
# ΔTm が None の基団があると融点は推定不可（沸点のみ可）
G = {
    "CH3":        (23.58, -5.10),
    "CH2":        (22.88, 11.27),
    "CH":         (21.74, 12.64),
    "Cq":         (18.25, 46.43),
    "CH2_ring":   (27.15, 7.75),
    "CH_ring":    (21.78, 19.88),
    "Cq_ring":    (21.32, 60.15),
    "dCH2":       (18.18, -4.32),
    "dCH":        (24.96, 8.73),
    "dC":         (24.14, 11.14),
    "dCH_ring":   (26.73, 8.13),
    "dC_ring":    (31.01, 37.02),
    "alleneC":    (26.15, 17.78),
    "tCH":        (9.20, -11.18),
    "tC":         (27.38, 64.32),
    "F":          (-0.03, -15.78),
    "Cl":         (38.13, 13.55),
    "Br":         (66.86, 43.43),
    "I":          (93.84, 41.69),
    "OH_alc":     (92.88, 44.45),
    "OH_phenol":  (76.34, 82.83),
    "O_nr":       (22.42, 22.23),
    "O_ring":     (31.22, 23.05),
    "ketone_nr":  (76.75, 61.20),
    "ketone_ring": (94.97, 75.97),
    "aldehyde":   (72.24, 36.90),
    "COOH":       (169.09, 155.50),
    "COO":        (81.10, 53.60),
    "NH2":        (73.23, 66.89),
    "NH_nr":      (50.17, 52.66),
    "NH_ring":    (52.82, 101.51),
    "N_nr":       (11.74, 48.84),
    "Ndr":        (74.60, None),     # -N= (non-ring): Tm 寄与なし
    "Nd_ring":    (57.55, 68.40),    # -N= (ring)
    "NH_imine":   (83.08, 68.91),    # =NH
    "CN":         (125.66, 59.89),
    "NO2":        (152.54, 127.24),
    "SH":         (63.56, 20.09),
    "S_nr":       (68.78, 34.40),
    "S_ring":     (52.10, 79.93),
}


def joback_estimate(smiles):
    """SMILES -> (Tb °C, Tm °C) 推定値。推定できない場合は None を含む / (None, None)。"""
    from rdkit import Chem
    from rdkit.Chem import rdchem

    if not smiles or "." in smiles:
        return (None, None)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return (None, None)

    BT = rdchem.BondType
    atoms = list(mol.GetAtoms())
    consumed = set()
    sum_tb = 0.0
    sum_tm = 0.0
    tm_ok = True

    def add(key):
        nonlocal sum_tb, sum_tm, tm_ok
        dtb, dtm = G[key]
        sum_tb += dtb
        if dtm is None:
            tm_ok = False
        else:
            sum_tm += dtm

    def bonds_to(atom):
        return {n.GetIdx(): b.GetBondType() for n, b in
                ((b.GetOtherAtom(atom), b) for b in atom.GetBonds())}

    # まず全原子の妥当性チェック（電荷・対象元素）
    for a in atoms:
        if a.GetFormalCharge() != 0:
            return (None, None)
        if a.GetSymbol() not in ("C", "N", "O", "S", "F", "Cl", "Br", "I", "H"):
            return (None, None)
        if a.GetSymbol() == "S" and any(b.GetBondType() in (BT.DOUBLE, BT.TRIPLE) for b in a.GetBonds()):
            return (None, None)

    # パス1: ニトロ基・ニトリル・カルボニル（基団が複数原子を含むもの）
    for a in atoms:
        if a.GetIdx() in consumed:
            continue
        sym = a.GetSymbol()
        bt = bonds_to(a)
        if sym == "N":
            oxy = [i for i, t in bt.items() if atoms[i].GetSymbol() == "O"]
            carb = [i for i, t in bt.items() if atoms[i].GetSymbol() == "C"]
            if len(oxy) == 2 and len(carb) == 1:
                add("NO2")
                consumed.add(a.GetIdx()); consumed.update(oxy)
            continue
        if sym != "C":
            continue
        # ニトリル炭素
        triple_n = [i for i, t in bt.items() if t == BT.TRIPLE and atoms[i].GetSymbol() == "N"]
        if triple_n:
            add("CN")
            consumed.add(a.GetIdx()); consumed.update(triple_n)
            continue
        # カルボニル炭素
        dbl_o = [i for i, t in bt.items() if t == BT.DOUBLE and atoms[i].GetSymbol() == "O"]
        if dbl_o:
            single_o = [i for i, t in bt.items() if t == BT.SINGLE and atoms[i].GetSymbol() == "O"]
            if single_o:
                o_atom = atoms[single_o[0]]
                other = [n for n in o_atom.GetNeighbors() if n.GetIdx() != a.GetIdx()]
                if other and other[0].GetSymbol() == "C":
                    add("COO")       # エステル（無水物含む）
                else:
                    add("COOH")      # カルボン酸
                consumed.add(single_o[0])
            elif a.GetTotalNumHs() >= 1:
                add("aldehyde")
            else:
                add("ketone_ring" if a.IsInRing() else "ketone_nr")
            consumed.add(a.GetIdx()); consumed.update(dbl_o)

    # パス2: 残りの原子を1原子ずつ分類
    for a in atoms:
        idx = a.GetIdx()
        if idx in consumed:
            continue
        sym = a.GetSymbol()
        bt = bonds_to(a)
        deg = a.GetDegree()
        in_ring = a.IsInRing()
        has_h = a.GetTotalNumHs() >= 1

        if sym == "C":
            types = list(bt.values())
            if types.count(BT.DOUBLE) == 2:
                add("alleneC")
            elif BT.TRIPLE in types:
                add("tCH" if deg == 1 else "tC")
            elif BT.DOUBLE in types or a.GetIsAromatic():
                if in_ring:
                    add("dCH_ring" if (deg == 2 and has_h) or (deg <= 2 and a.GetIsAromatic() and has_h) else "dC_ring")
                else:
                    add("dCH2" if deg == 1 else ("dCH" if deg == 2 else "dC"))
            else:
                if in_ring:
                    add("CH2_ring" if deg == 2 else ("CH_ring" if deg == 3 else "Cq_ring"))
                else:
                    add("CH3" if deg <= 1 else ("CH2" if deg == 2 else ("CH" if deg == 3 else "Cq")))
        elif sym == "O":
            if deg == 1:
                if not has_h:
                    return (None, None)  # 末端 =O / O- など対象外
                neighbor = atoms[next(iter(bt))]
                add("OH_phenol" if neighbor.GetIsAromatic() else "OH_alc")
            elif deg == 2 and all(t == BT.SINGLE or t == BT.AROMATIC for t in bt.values()):
                add("O_ring" if in_ring else "O_nr")
            else:
                return (None, None)
        elif sym == "N":
            if a.GetIsAromatic():
                if deg == 2 and has_h:
                    add("NH_ring")
                elif deg == 2:
                    add("Nd_ring")
                else:
                    add("N_nr")  # 環内3級アミン相当は非環値で近似
            elif any(t == BT.DOUBLE for t in bt.values()):
                partner = atoms[next(i for i, t in bt.items() if t == BT.DOUBLE)]
                if partner.GetSymbol() != "C":
                    return (None, None)  # アゾ等は対象外
                add("NH_imine" if has_h else "Ndr")
            elif any(t == BT.TRIPLE for t in bt.values()):
                return (None, None)  # ニトリルNはパス1で消費済みのはず
            else:
                if deg == 1:
                    add("NH2")
                elif deg == 2:
                    add("NH_ring" if in_ring else "NH_nr")
                elif deg == 3:
                    add("N_nr")
                else:
                    return (None, None)
        elif sym == "S":
            if deg == 1 and has_h:
                add("SH")
            elif deg == 2:
                add("S_ring" if in_ring else "S_nr")
            else:
                return (None, None)
        elif sym in ("F", "Cl", "Br", "I"):
            if deg != 1:
                return (None, None)
            add(sym)
        else:
            return (None, None)
        consumed.add(idx)

    tb_c = 198.2 + sum_tb - 273.15
    tm_c = (122.5 + sum_tm - 273.15) if tm_ok else None
    return (tb_c, tm_c)


def parse_exp_celsius(text):
    """実験値文字列 '77.1 °C' / '52-54 °C' / '313 °F ...' -> °C の float、不発は None"""
    if not text:
        return None
    m = re.match(r"^\[?(-?\d+(?:\.\d+)?)", str(text))
    if not m:
        return None
    v = float(m.group(1))
    if "°F" in str(text):
        return (v - 32) * 5 / 9
    if "°C" in str(text):
        return v
    return None


def validate(db):
    rows = db.execute(
        "SELECT smiles, melting_point, boiling_point FROM compounds "
        "WHERE smiles IS NOT NULL AND smiles != ''").fetchall()
    errs_tm, errs_tb = [], []
    skipped = 0
    for smi, mp, bp in rows:
        exp_tm, exp_tb = parse_exp_celsius(mp), parse_exp_celsius(bp)
        if exp_tm is None and exp_tb is None:
            continue
        est_tb, est_tm = joback_estimate(smi)
        if est_tb is None and est_tm is None:
            skipped += 1
            continue
        if exp_tb is not None and est_tb is not None:
            errs_tb.append(abs(est_tb - exp_tb))
        if exp_tm is not None and est_tm is not None:
            errs_tm.append(abs(est_tm - exp_tm))
    import statistics
    print(f"validation targets (with exp values): Tb {len(errs_tb)}, Tm {len(errs_tm)}, unestimable {skipped}")
    if errs_tb:
        print(f"  Tb MAE = {statistics.mean(errs_tb):.1f} K, median = {statistics.median(errs_tb):.1f} K")
    if errs_tm:
        print(f"  Tm MAE = {statistics.mean(errs_tm):.1f} K, median = {statistics.median(errs_tm):.1f} K")


def joback_fill(db):
    rows = db.execute(
        "SELECT id, smiles FROM compounds WHERE smiles IS NOT NULL AND smiles != '' "
        "AND ((melting_point IS NULL OR melting_point='') OR (boiling_point IS NULL OR boiling_point=''))"
    ).fetchall()
    print(f"joback targets: {len(rows)}")
    mp_filled = bp_filled = none_filled = 0
    for cid_id, smi in rows:
        cur_mp, cur_bp = db.execute(
            "SELECT melting_point, boiling_point FROM compounds WHERE id=?", (cid_id,)).fetchone()
        est_tb, est_tm = joback_estimate(smi)
        if est_tm is not None and is_empty(cur_mp):
            db.execute("UPDATE compounds SET melting_point=? WHERE id=?",
                       (f"{est_tm:.0f} °C（推定）", cid_id))
            mp_filled += 1
        if est_tb is not None and is_empty(cur_bp):
            db.execute("UPDATE compounds SET boiling_point=? WHERE id=?",
                       (f"{est_tb:.0f} °C（推定）", cid_id))
            bp_filled += 1
        if est_tb is None and est_tm is None:
            none_filled += 1
    db.commit()
    print(f"joback filled: mp +{mp_filled}, bp +{bp_filled}, unestimable {none_filled}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "validate"
    db = sqlite3.connect(DB_PATH)
    if mode == "validate":
        validate(db)
    elif mode == "wikidata":
        wikidata_fill(db)
    elif mode == "joback":
        joback_fill(db)
    elif mode == "all":
        wikidata_fill(db)
        joback_fill(db)
    else:
        print("unknown mode:", mode)
    db.close()


if __name__ == "__main__":
    main()
