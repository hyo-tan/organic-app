# Phase 3: スペクトル解析

## バックエンド (backend/analysis.py)
- `POST /api/analysis/parse` — xlsx（全シート）/ csv をアップロードし、2列の数値データを系列として返す。描画用に最大6000点へ間引き
- `POST /api/analysis/peaks` — scipy.signal.find_peaks でピーク検出。invert=true で透過率IRなど下向きピークに対応
- `POST /api/analysis/compare` — 検出ピークと curated 200件のピークリストを照合し候補をランク付け
  - 許容幅: IR ±25 cm⁻¹（範囲表記は中点で代表）、EI-MS ±0.6、¹H NMR ±0.15 ppm、¹³C NMR ±0.6 ppm
  - スコア = 一致したDBピーク数 / DBピーク総数。同点は一致数→名前順
- requirements.txt に scipy / openpyxl / python-multipart を追加（未導入環境では解析APIだけ無効化）

## フロントエンド (app/analysis/page.tsx)
- 種類切替 (IR / EI-MS / ¹H NMR / ¹³C NMR)：軸タイトルと反転（IR・NMRは軸反転）
- xlsx/csv の複数ファイル・複数シート読み込みと Plotly での重ね描き、縦軸正規化
- 系列ごとのピーク検出（マーカー表示）とピーク位置一覧
- DB比較：候補カード（スコア・一致/不一致ピークと帰属）、候補のDBスペクトル曲線を破線で重ね描き

## 検証 (2026-11-01)
- API: DB収録IR曲線から作った xlsx で 酢酸エチル / エタノール / アセトン がいずれも候補1位 (スコア1.0)。EI-MS でもエタノールが1位
- 画面: ヘッドレスブラウザで アップロード→ピーク検出→DB比較→DBスペクトル重ね描き まで実操作確認、JSエラーなし
