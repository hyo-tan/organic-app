"""
PubChem から化合物データを一括取得して SQLite に取り込むパイプライン (Phase 1: 1万件化)

使い方:
    python fetch_pubchem_bulk.py --target 10000            # 合計1万件を目標にCID走査で収集
    python fetch_pubchem_bulk.py --target 1200 --with-experimental   # 実験物性(mp/bp/密度)も取得（低速・再開可能）

設計:
- Stage A (高速): CID を若い順に走査し、PUG REST のバッチAPIで基本プロパティ+同義語を取得。
  CID の若い化合物ほど古典的でよく知られた物質が多い。有機・単成分・中性・MW 30〜1000 に絞る。
  進捗 (走査済みCID) は DB の meta に保存するので、中断しても再実行で続きから再開できる。
- Stage B (--with-experimental): PUG VIEW を1件ずつ叩いて実験の融点・沸点・密度を補完する。
  既存スクリプト fetch_basic_properties_pubchem.py と同じ見出しで抽出。処理済みCIDを meta に記録し再開可能。
- 既存の curated データとは InChIKey で重複判定し、上書きしない。
- 日本語名は PubChem の同義語に日本語が含まれていれば採用する（無ければ空欄）。
"""
from __future__ import annotations

import argparse
import json
import re
import time

import requests

import db as dblayer

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUG_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
PROPS = "MolecularFormula,MolecularWeight,CanonicalSMILES,IsomericSMILES,IUPACName,InChIKey,Title,XLogP,TPSA,Charge"
BATCH = 200          # PUG REST バッチサイズ
CID_CHUNK = 2000     # 1回の走査チャンク（この中から条件に合うものを採用）
REQ_SLEEP = 0.25     # PubChem のレート制限 (5 req/s) 内に収める

JP_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


def post_json(url: str, data: dict, timeout: int = 60) -> dict | None:
    for attempt in range(3):
        try:
            r = requests.post(url, data=data, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 503):
                time.sleep(2 * (attempt + 1))
                continue
            return None
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    return None


def get_json(url: str, timeout: int = 30) -> dict | None:
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 503):
                time.sleep(2 * (attempt + 1))
                continue
            return None
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    return None


def is_target_organic(p: dict) -> bool:
    formula = p.get("MolecularFormula") or ""
    smiles = p.get("CanonicalSMILES") or ""
    if "C" not in formula:
        return False
    if "." in smiles:  # 塩・混合物などの複数成分は除外
        return False
    if p.get("Charge", 0) != 0:
        return False
    try:
        mw = float(p.get("MolecularWeight") or 0)
    except (TypeError, ValueError):
        return False
    if not (30 <= mw <= 1000):
        return False
    if not p.get("IUPACName") or not p.get("InChIKey"):
        return False
    return True


def stage_a(con, target_total: int) -> None:
    """CID走査で基本データを集める。target_total はDB全体の目標件数。"""
    total = dblayer.count_compounds(con)
    next_cid = int(dblayer.get_meta(con, "scan_next_cid") or "1")
    print(f"[stage A] start: total={total}, target={target_total}, scan from CID {next_cid}")

    while total < target_total:
        cids = list(range(next_cid, next_cid + CID_CHUNK))
        added = 0
        for i in range(0, len(cids), BATCH):
            batch = cids[i : i + BATCH]
            data = post_json(
                f"{PUG}/compound/cid/property/{PROPS}/JSON",
                {"cid": ",".join(map(str, batch))},
            )
            time.sleep(REQ_SLEEP)
            if not data:
                continue
            props = {p["CID"]: p for p in data.get("PropertyTable", {}).get("Properties", [])}
            candidates = [cid for cid in batch if cid in props and is_target_organic(props[cid])]
            if not candidates:
                continue
            # 同義語をバッチ取得（一般名と日本語名の候補）
            syn = post_json(f"{PUG}/compound/cid/synonyms/JSON", {"cid": ",".join(map(str, candidates))})
            time.sleep(REQ_SLEEP)
            synmap: dict[int, list[str]] = {}
            if syn:
                for item in syn.get("InformationList", {}).get("Information", []):
                    synmap[item["CID"]] = item.get("Synonym", []) or []

            for cid in candidates:
                if total >= target_total:
                    break
                p = props[cid]
                synonyms = synmap.get(cid, [])
                name_ja = next((s for s in synonyms if JP_RE.search(s) and len(s) <= 40), None)
                row = {
                    "cid": cid,
                    "cas": None,
                    "name_ja": name_ja,
                    "name_en": p.get("Title"),
                    "iupac_name": p.get("IUPACName"),
                    "formula": p.get("MolecularFormula"),
                    "mw": float(p["MolecularWeight"]) if p.get("MolecularWeight") else None,
                    "smiles": p.get("IsomericSMILES") or p.get("CanonicalSMILES"),
                    "inchi_key": p.get("InChIKey"),
                    "melting_point": None,
                    "boiling_point": None,
                    "density": None,
                    "state": None,
                    "category": None,
                    "data_quality": "pubchem-basic",
                    "tier": "pubchem",
                    "synonyms": synonyms[:30],
                }
                before = dblayer.count_compounds(con)
                dblayer.upsert_compound(con, row)
                total = dblayer.count_compounds(con)
                if total > before:
                    added += 1
        next_cid += CID_CHUNK
        dblayer.set_meta(con, "scan_next_cid", str(next_cid))
        con.commit()
        print(f"[stage A] scanned up to CID {next_cid - 1}: total={total} (+{added} in this chunk)")

    print(f"[stage A] done: total={total}")


# ---- Stage B: 実験物性 (PUG VIEW) ----
TARGET_HEADINGS = {
    "melting_point": ["Melting Point", "Experimental Melting Point"],
    "boiling_point": ["Boiling Point", "Experimental Boiling Point"],
    "density": ["Density", "Experimental Density"],
}


def _extract_text(value_obj: dict) -> str:
    if "StringWithMarkup" in value_obj:
        texts = [it.get("String", "") for it in value_obj["StringWithMarkup"] if isinstance(it, dict)]
        return "; ".join(t for t in texts if t).strip()
    if "Number" in value_obj:
        unit = value_obj.get("Unit") or ""
        return f"{value_obj['Number']} {unit}".strip()
    if "String" in value_obj:
        return str(value_obj["String"]).strip()
    return ""


def _walk_sections(node, headings: set[str], out: dict[str, str]) -> None:
    if isinstance(node, dict):
        heading = node.get("TOCHeading")
        if heading in headings and "Information" in node:
            for info in node["Information"]:
                val = _extract_text(info.get("Value", {}))
                if val and heading not in out:
                    out[heading] = val
        for v in node.values():
            _walk_sections(v, headings, out)
    elif isinstance(node, list):
        for v in node:
            _walk_sections(v, headings, out)


def fetch_experimental(cid: int) -> dict[str, str]:
    data = get_json(f"{PUG_VIEW}/data/compound/{cid}/JSON?heading=Experimental+Properties")
    if not data:
        return {}
    all_headings = {h for hs in TARGET_HEADINGS.values() for h in hs}
    found: dict[str, str] = {}
    _walk_sections(data, all_headings, found)
    result = {}
    for key, headings in TARGET_HEADINGS.items():
        for h in headings:
            if h in found:
                result[key] = found[h]
                break
    return result


def stage_b(con, limit: int | None = None) -> None:
    """実験物性が未取得の pubchem 行を PUG VIEW で補完する（再開可能）。"""
    rows = con.execute(
        """SELECT id, cid FROM compounds
           WHERE tier='pubchem' AND cid IS NOT NULL
             AND (melting_point IS NULL AND boiling_point IS NULL AND density IS NULL)
           ORDER BY cid"""
    ).fetchall()
    if limit:
        rows = rows[:limit]
    print(f"[stage B] targets: {len(rows)} compounds")
    done = 0
    for r in rows:
        props = fetch_experimental(int(r["cid"]))
        time.sleep(0.25)
        if props:
            sets = ", ".join(f"{k}=?" for k in props)
            con.execute(f"UPDATE compounds SET {sets} WHERE id=?", (*props.values(), r["id"]))
            done += 1
        if (done % 50) == 0:
            con.commit()
    con.commit()
    print(f"[stage B] done: experimental props filled for {done} compounds")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=10000, help="DB全体の目標件数 (stage A)")
    ap.add_argument("--with-experimental", action="store_true", help="stage B も実行する")
    ap.add_argument("--experimental-limit", type=int, default=None)
    ap.add_argument("--skip-a", action="store_true")
    args = ap.parse_args()

    con = dblayer.connect()
    dblayer.init_db(con)
    if not args.skip_a:
        stage_a(con, args.target)
    if args.with_experimental:
        stage_b(con, args.experimental_limit)
    con.close()


if __name__ == "__main__":
    main()
