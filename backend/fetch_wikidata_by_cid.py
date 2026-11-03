"""
Wikidata から日本語名と CAS 番号を補完するスクリプト (Phase 1.6)

fetch_wikidata_ja.py は InChIKey (P235) で突き合わせたが、Wikidata 側に
InChIKey が無い・別形で登録されている項目を取りこぼす。ここでは
PubChem CID (P662) をキーに再照会し、日本語ラベル (rdfs:label@ja /
skos:altLabel@ja) と CAS 登録番号 (P231) を取り込む。
値が取れた行だけを更新し、既存の name_ja / cas は上書きしない。再実行しても安全。

使い方:
    python fetch_wikidata_by_cid.py [--chunk 200]
"""
from __future__ import annotations

import argparse
import time

import requests

import db as dblayer

SPARQL = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "OrganicCompoundTool/0.1 (educational project)",
    "Accept": "application/sparql-results+json",
}


def query_chunk(cids: list[str]) -> dict[str, dict[str, str]]:
    values = " ".join(f'"{c}"' for c in cids)
    sparql = f"""
    SELECT ?cid ?label ?alt ?cas WHERE {{
      VALUES ?cid {{ {values} }}
      ?item wdt:P662 ?cid .
      OPTIONAL {{ ?item wdt:P231 ?cas . }}
      OPTIONAL {{ ?item rdfs:label ?label . FILTER(lang(?label) = "ja") }}
      OPTIONAL {{ ?item skos:altLabel ?alt . FILTER(lang(?alt) = "ja") }}
    }}
    """
    for attempt in range(3):
        try:
            r = requests.post(SPARQL, data={"query": sparql, "format": "json"}, headers=HEADERS, timeout=120)
            if r.status_code == 200:
                out: dict[str, dict[str, str]] = {}
                for b in r.json()["results"]["bindings"]:
                    cid = b["cid"]["value"]
                    entry = out.setdefault(cid, {})
                    if "label" in b:
                        entry["name_ja"] = b["label"]["value"]
                    elif "alt" in b and "name_ja" not in entry:
                        entry["name_ja"] = b["alt"]["value"]
                    if "cas" in b and "cas" not in entry:
                        entry["cas"] = b["cas"]["value"]
                return out
            if r.status_code in (429, 503):
                time.sleep(5 * (attempt + 1))
                continue
            print(f"  [warn] SPARQL status {r.status_code}", flush=True)
            return {}
        except requests.RequestException as e:
            print(f"  [warn] SPARQL error: {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=200)
    args = ap.parse_args()

    con = dblayer.connect()
    try:
        rows = con.execute(
            "SELECT id, cid, name_ja, cas FROM compounds WHERE cid IS NOT NULL "
            "AND ((name_ja IS NULL OR name_ja='') OR (cas IS NULL OR cas=''))"
        ).fetchall()
        targets = [r for r in rows]
        print(f"targets (missing name_ja or cas, with CID): {len(targets)}", flush=True)

        by_cid = {str(r["cid"]): r for r in targets}
        cids = list(by_cid.keys())
        got_name = 0
        got_cas = 0
        for i in range(0, len(cids), args.chunk):
            chunk = cids[i : i + args.chunk]
            result = query_chunk(chunk)
            for cid, entry in result.items():
                row = by_cid.get(cid)
                if row is None:
                    continue
                if entry.get("name_ja") and not row["name_ja"]:
                    con.execute("UPDATE compounds SET name_ja=? WHERE id=?", (entry["name_ja"], row["id"]))
                    got_name += 1
                if entry.get("cas") and not row["cas"]:
                    # cas は UNIQUE 制約があるため、既存と衝突する場合は取り込まない
                    clash = con.execute("SELECT id FROM compounds WHERE cas=?", (entry["cas"],)).fetchone()
                    if clash is None:
                        con.execute("UPDATE compounds SET cas=? WHERE id=?", (entry["cas"], row["id"]))
                        got_cas += 1
            con.commit()
            print(f"  {min(i + args.chunk, len(cids))}/{len(cids)} done (names +{got_name}, cas +{got_cas})", flush=True)
            time.sleep(1)

        total_name = con.execute("SELECT COUNT(*) FROM compounds WHERE name_ja IS NOT NULL AND name_ja != ''").fetchone()[0]
        total_cas = con.execute("SELECT COUNT(*) FROM compounds WHERE cas IS NOT NULL AND cas != ''").fetchone()[0]
        print(f"added: name_ja +{got_name}, cas +{got_cas}")
        print(f"totals now: name_ja {total_name}, cas {total_cas}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
