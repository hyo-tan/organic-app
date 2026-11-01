# Phase 1: DB化 + 1万件化

## 変更点
- `db.py` — SQLite データ層。化合物・ピーク・スペクトル曲線（zlib圧縮BLOB）・同義語を保持。
- `migrate_to_db.py` — 既存の `compounds.json` と `spectra/*.json` を `compounds.db` に移行（tier='curated'）。
- `fetch_pubchem_bulk.py` — PubChem から一括取得するパイプライン。
- `main.py` — `compounds.db` があれば DB を正本として読み、無ければ従来JSONにフォールバック。スペクトルAPIもDB優先。

## 使い方
```bash
cd backend
python migrate_to_db.py                       # 200件をDB化
python fetch_pubchem_bulk.py --target 10000   # Stage A: 基本データを1万件まで収集（再開可能）
python fetch_pubchem_bulk.py --skip-a --with-experimental            # Stage B: 実験物性(融点/沸点/密度)を補完
python fetch_pubchem_bulk.py --skip-a --with-experimental --experimental-limit 500
uvicorn main:app --reload                     # API起動（DBがあればDBから配信）
```

## パイプライン設計
- **Stage A（高速）**: PubChem の CID を若い順に走査し、バッチAPIで基本プロパティと同義語を取得。
  有機・単成分・中性・分子量30〜1000 に限定。進捗は DB の meta テーブルに保存され、中断しても再開できる。
  既存 curated データとは InChIKey で重複判定し上書きしない。新規行は tier='pubchem', data_quality='pubchem-basic'。
- **Stage B（低速・任意）**: PUG VIEW を1件ずつ参照し、実験の融点・沸点・密度を補完する。
  約0.8秒/件で、値がある化合物は一部のみ。全件分は数時間かかるため、ミニPCでの夜間実行を想定。
- 日本語名は PubChem 同義語に日本語が含まれる場合のみ採用（現状ほぼ無し）。
  将来の改善案: Wikidata の日本語ラベルを InChIKey / CAS で突き合わせて補完する。

## データ規模の目安（実測）
- 移行直後: 200件 + スペクトル800件で DB 約2.0MB（元JSON約20MB）
- 検索: 名前/分子式/CAS で 0.1〜0.2 ms 程度
