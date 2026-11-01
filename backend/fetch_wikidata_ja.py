"""
Wikidata から日本語名と CAS 番号を補完するスクリプト (Phase 1.5)

PubChem 拡張分 (tier='pubchem') は日本語名がほぼ空欄なため、InChIKey (Wikidata P235) で
突き合わせて、日本語ラベル (rdfs:label@ja) と CAS 登録番号 (P231) を取り込む。
値が取れた行だけを更新し、既存の name_ja / cas は上書きしない。再実行しても安全。

使い方:
    python fetch_wikidata_ja.py [--chunk 400]
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


def query_chunk(inchi_keys: list[str]) -> dict[str, dict[str, str]]:
    values = " ".join(f'"{k}"' for k in inchi_keys)
    sparql = f"""
    SELECT ?ik ?label ?cas WHERE {{
      VALUES ?ik {{ {values} }}
      ?item wdt:P235 ?ik .
      OPTIONAL {{ ?item wdt:P231 ?cas . }}
      OPTIONAL {{ ?item rdfs:label ?label . FILTER(lang(?label) = "ja") }}
    }}
    """
    for attempt in range(3):
        try:
            # 大きな VALUES は GET だと URL 長制限・タイムアウトに当たるため POST で送る
            r = requests.post(SPARQL, data={"query": sparql, "format": "json"}, headers=HEADERS, timeout=120)
            if r.status_code == 200:
                out: dict[str, dict[str, str]] = {}
                for b in r.json()["results"]["bindings"]:
                    ik = b["ik"]["value"]
                    entry = out.setdefault(ik, {})
                    if "label" in b:
                        entry["name_ja"] = b["label"]["value"]
                    if "cas" in b:
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


def apply_mapping(db_path: str, mapping_path: str) -> None:
    """--dump で保存した {inchi_key: {name_ja, cas}} を対象DBへ一括適用する（短時間トランザクション）。"""
    import json
    from pathlib import Path

    mapping = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    con = dblayer.connect(Path(db_path))
    n_label = n_cas = 0
    for ik, vals in mapping.items():
        r = con.execute("SELECT id, name_ja, cas FROM compounds WHERE inchi_key=?", (ik,)).fetchone()
        if not r:
            continue
        if vals.get("name_ja") and not r["name_ja"]:
            con.execute("UPDATE compounds SET name_ja=? WHERE id=?", (vals["name_ja"], r["id"]))
            n_label += 1
        if vals.get("cas") and not r["cas"]:
            try:
                con.execute("UPDATE compounds SET cas=? WHERE id=?", (vals["cas"], r["id"]))
                n_cas += 1
            except Exception:
                pass
    con.commit()
    con.close()
    print(f"applied: labels +{n_label}, cas +{n_cas}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=50, help="1回のSPARQLに載せるキー数（大きいと公共エンドポイントがタイムアウトする）")
    ap.add_argument("--db", default=None, help="対象DB (既定は compounds.db)。Stage B 実行中はコピーを指定して競合を避ける")
    ap.add_argument("--dump", default=None, help="取得結果を {inchi_key: {...}} の JSON にも保存する")
    ap.add_argument("--apply", default=None, help="保存済み JSON を --db に適用して終了する")
    args = ap.parse_args()

    if args.apply:
        apply_mapping(args.db or str(dblayer.DB_PATH), args.apply)
        return

    from pathlib import Path

    con = dblayer.connect(Path(args.db) if args.db else None)
    dblayer.init_db(con)
    rows = con.execute(
        """SELECT id, inchi_key, name_ja, cas FROM compounds
           WHERE inchi_key IS NOT NULL AND (name_ja IS NULL OR cas IS NULL)"""
    ).fetchall()
    print(f"targets: {len(rows)} compounds", flush=True)

    by_key = {r["inchi_key"]: r for r in rows}
    keys = list(by_key.keys())
    n_label = n_cas = 0
    collected: dict[str, dict[str, str]] = {}
    for i in range(0, len(keys), args.chunk):
        chunk = keys[i : i + args.chunk]
        found = query_chunk(chunk)
        collected.update(found)
        for ik, vals in found.items():
            r = by_key[ik]
            sets, params = [], []
            if vals.get("name_ja") and not r["name_ja"]:
                sets.append("name_ja=?")
                params.append(vals["name_ja"])
                n_label += 1
            if vals.get("cas") and not r["cas"]:
                # CAS の重複（既存 curated と衝突）は UNIQUE 制約で弾かれるので個別に試す
                try:
                    con.execute("UPDATE compounds SET cas=? WHERE id=?", (vals["cas"], r["id"]))
                    n_cas += 1
                except Exception:
                    pass
            if sets:
                con.execute(f"UPDATE compounds SET {', '.join(sets)} WHERE id=?", (*params, r["id"]))
        con.commit()
        print(f"progress: {min(i + args.chunk, len(keys))}/{len(keys)} keys, labels +{n_label}, cas +{n_cas}", flush=True)
        time.sleep(1.0)

    print(f"done: japanese labels filled {n_label}, cas filled {n_cas}", flush=True)
    if args.dump:
        import json
        from pathlib import Path

        Path(args.dump).write_text(json.dumps(collected, ensure_ascii=False), encoding="utf-8")
        print(f"dumped mapping for {len(collected)} keys -> {args.dump}", flush=True)
    con.close()


if __name__ == "__main__":
    main()
