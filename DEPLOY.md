# 本番公開の構成（2026-11-02 時点）

- フロント: Cloudflare Pages — https://organic-compound-app.pages.dev
  （GitHub main への push で自動ビルド＆デプロイ。ルートは frontend/、ビルドは `npm run build`）
- API: Render — https://organic-compound-api.onrender.com
  （GitHub main への push で自動デプロイ。compounds.db はリポジトリに含めて管理する）
- 同名の Cloudflare Workers プロジェクトは旧・手動デプロイの残骸で、Git 連携は解除済み（未使用）。

以下はミニPC（自宅サーバー）へ移す場合の手順。

# ミニPCへのデプロイ手順（自宅サーバー）

前提: Linux (Ubuntu Server LTS / Debian 想定)、メモリ16GB、Docker Engine + Compose プラグイン導入済み。

## 1. コードとDBを用意する

```bash
git clone https://github.com/hyo-tan/organic-app.git
cd organic-app/backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt requests
python migrate_to_db.py                    # 既存200件をDB化
python fetch_pubchem_bulk.py --target 10000  # 1万件まで収集（初回のみ・数分）
python fetch_wikidata_ja.py                # 日本語名・CASを補完（任意）
deactivate
```

すでに compounds.db を持っている場合は、そのファイルを backend/ に置くだけでよい。

## 2. 起動

```bash
cd organic-app
docker compose up -d --build
```

- Web: `http://<ミニPCのIP>:8080`（検索 / 構造式エディタ / スペクトル解析）
- API: `http://<ミニPCのIP>:8000`（/api/health で疎通確認）

フロントは、LAN内IPや `.local` でアクセスされた場合に同じホストの8000番APIへ自動接続する
（`frontend/app/lib/api.ts`）。別の接続先にしたい場合は環境変数 `NEXT_PUBLIC_API_BASE_URL` を使う。

## 3. データの更新（任意・夜間バッチ想定）

実験物性（融点・沸点・密度）の補完は低速（約0.8秒/件）なので夜間に回す:

```bash
cd backend && . .venv/bin/activate
python fetch_pubchem_bulk.py --skip-a --with-experimental   # 中断しても再開可能
docker compose restart api
```

## 4. 外出先から使う場合

公開せず、Tailscale 経由で自分の端末からだけアクセスするのがおすすめ
（ミニPCとスマホ/PCを同じ tailnet に入れ、Tailscale のIPで開く）。
その場合は `NEXT_PUBLIC_API_BASE_URL` の設定は不要で、Tailscale のホスト名/IPでも
上記の自動判定が効く範囲（100.x.x.x は対象外）があるため、必要なら
`NEXT_PUBLIC_API_BASE_URL=http://<tailscale-ip>:8000` を指定してフロントを再ビルドする。
