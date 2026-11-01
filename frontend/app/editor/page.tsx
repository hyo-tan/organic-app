"use client";

// Phase 2: 構造式描画ページ。Ketcher はブラウザ専用ライブラリのため ssr: false で読み込む。
import dynamic from "next/dynamic";
import Link from "next/link";

const KetcherPanel = dynamic(() => import("../../components/KetcherPanel"), {
  ssr: false,
  loading: () => <p className="text-sm text-gray-600">エディタを読み込み中...</p>,
});

export default function EditorPage() {
  return (
    <main className="min-h-screen bg-gray-50 px-4 py-6">
      <div className="max-w-6xl mx-auto flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">構造式エディタ</h1>
          <div className="flex gap-2">
            <Link href="/analysis" className="border rounded px-3 py-2 bg-white hover:bg-gray-100 text-sm">
              スペクトル解析
            </Link>
            <Link href="/" className="border rounded px-3 py-2 bg-white hover:bg-gray-100 text-sm">
              ← 化合物検索に戻る
            </Link>
          </div>
        </div>
        <p className="text-sm text-gray-700">
          構造式を描くと、分子式・分子量の計算、データベース照合、立体異性体の列挙、3D表示、画像の書き出しができます。
          計算値は RDKit による生成データです。
        </p>
        <KetcherPanel />
      </div>
    </main>
  );
}
