# Phase 2: 構造式描画

## バックエンド (backend/structure.py, RDKit)
- `GET /api/structure/depict?smiles=&format=svg|png&width=&height=` — SMILES から構造式画像を自前描画（外部サービス不要）
- `POST /api/structure/analyze` {smiles | molblock} — 分子式・分子量・精密質量・InChIKey + DB照合（InChIKey 一致）
- `POST /api/structure/stereoisomers` {smiles | molblock, max_isomers} — 立体異性体の列挙（SVG付き）
- `POST /api/structure/conformer` {smiles | molblock} — ETKDG で3D配座生成 + MMFF/UFF 最適化、MolBlock とエネルギーを返す
- requirements.txt に rdkit を追加。未導入環境では main.py が構造APIだけ無効化して起動する。

## フロントエンド
- `/editor` ページ（app/editor/page.tsx + components/KetcherPanel.tsx）
  - Ketcher エディタ（OSS、ChemDraw 風）。SMILES の読み込みにも対応
  - 解析 / 立体異性体グリッド / 3D表示 (3Dmol.js) / SVG・PNG 保存
- 検索ページの構造式画像を NIH Cactus から自前 depict API に切替（SMILES が無い場合のみ PubChem 画像）
- API 接続先を app/lib/api.ts に共通化：localhost では http://localhost:8000、公開環境では Render

## 検証 (2026-11-01)
- next build 成功（/ と /editor）
- ヘッドレスブラウザで実操作確認：エディタ描画、SMILES 読込、解析（酢酸エチルで DB 照合一致）、3D 表示
