"use client";

// Phase 2: 構造式エディタ (Ketcher) + RDKit 連携パネル
// - 描いた構造の解析（分子式・分子量・InChIKey、DB照合）
// - 立体異性体の列挙、3D配座の表示 (3Dmol.js)、画像 (SVG/PNG) 書き出し
import { useRef, useState } from "react";
import { Editor } from "ketcher-react";
import { StandaloneStructServiceProvider } from "ketcher-standalone";
import type { Ketcher } from "ketcher-core";
import "ketcher-react/dist/index.css";
import { getApiBaseUrl } from "../app/lib/api";

const structServiceProvider = new StandaloneStructServiceProvider();

type AnalyzeResult = {
  formula: string;
  mw: number;
  exact_mass: number;
  canonical_smiles: string;
  isomeric_smiles: string;
  inchi_key: string;
  db_match: {
    name_ja: string | null;
    name_en: string | null;
    cas: string | null;
    tier: string;
  } | null;
};

type Isomer = { smiles: string; svg: string };

export default function KetcherPanel() {
  const ketcherRef = useRef<Ketcher | null>(null);
  const viewerHostRef = useRef<HTMLDivElement | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const viewerRef = useRef<any>(null);

  const [smilesInput, setSmilesInput] = useState("");
  const [currentSmiles, setCurrentSmiles] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [isomers, setIsomers] = useState<Isomer[] | null>(null);
  const [energy, setEnergy] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const api = getApiBaseUrl();

  const post = async (path: string, body: object) => {
    const res = await fetch(`${api}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text.slice(0, 200)}`);
    }
    return res.json();
  };

  const getMolblock = async (): Promise<string> => {
    const ketcher = ketcherRef.current;
    if (!ketcher) throw new Error("エディタの初期化中です。少し待ってからお試しください。");
    const molblock = await ketcher.getMolfile();
    setCurrentSmiles(await ketcher.getSmiles());
    return molblock;
  };

  const runAnalyze = async () => {
    setBusy(true);
    setMessage("");
    try {
      const molblock = await getMolblock();
      setAnalysis(await post("/api/structure/analyze", { molblock }));
    } catch (e) {
      setMessage(`解析に失敗しました: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(false);
    }
  };

  const runStereoisomers = async () => {
    setBusy(true);
    setMessage("");
    try {
      const molblock = await getMolblock();
      const data = await post("/api/structure/stereoisomers", { molblock, max_isomers: 32 });
      setIsomers(data.isomers);
      if (data.count <= 1) {
        setMessage("列挙できる立体異性体は1つだけでした（立体中心が未指定でない、または立体中心がありません）。");
      }
    } catch (e) {
      setMessage(`立体異性体の列挙に失敗しました: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(false);
    }
  };

  const runConformer = async () => {
    setBusy(true);
    setMessage("");
    try {
      const molblock = await getMolblock();
      const data = await post("/api/structure/conformer", { molblock });
      setEnergy(data.energy_kcal_mol);
      const $3Dmol = (await import("3dmol")).default ?? (await import("3dmol"));
      if (viewerHostRef.current) {
        if (!viewerRef.current) {
          viewerRef.current = $3Dmol.createViewer(viewerHostRef.current, {
            backgroundColor: "white",
          });
        }
        const viewer = viewerRef.current;
        viewer.clear();
        viewer.addModel(data.molblock, "mol");
        viewer.setStyle({}, { stick: { radius: 0.14 }, sphere: { scale: 0.28 } });
        viewer.zoomTo();
        viewer.render();
      }
    } catch (e) {
      setMessage(`3D配座の生成に失敗しました: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(false);
    }
  };

  const loadSmilesIntoEditor = async () => {
    const ketcher = ketcherRef.current;
    if (!ketcher || !smilesInput.trim()) return;
    setMessage("");
    try {
      await ketcher.setMolecule(smilesInput.trim());
      setCurrentSmiles(smilesInput.trim());
    } catch {
      setMessage("SMILES を読み込めませんでした。表記を確認してください。");
    }
  };

  const downloadUrl = (format: "svg" | "png") =>
    currentSmiles
      ? `${api}/api/structure/depict?smiles=${encodeURIComponent(currentSmiles)}&format=${format}&width=900&height=760`
      : "";

  const btn =
    "border rounded px-3 py-2 bg-white hover:bg-gray-100 disabled:opacity-50 text-sm";

  return (
    <div className="flex flex-col gap-4">
      <div className="border rounded bg-white" style={{ height: "62vh", minHeight: 420 }}>
        <Editor
          staticResourcesUrl=""
          structServiceProvider={structServiceProvider}
          onInit={(ketcher) => {
            ketcherRef.current = ketcher;
          }}
          errorHandler={(msg: string) => setMessage(msg)}
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={smilesInput}
          onChange={(e) => setSmilesInput(e.target.value)}
          placeholder="SMILES を貼り付け（例: CCOC(=O)C）"
          className="border rounded px-3 py-2 flex-1 min-w-64 text-sm"
        />
        <button className={btn} onClick={loadSmilesIntoEditor}>
          エディタに読み込む
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <button className={btn} disabled={busy} onClick={runAnalyze}>
          構造を解析（物性・DB照合）
        </button>
        <button className={btn} disabled={busy} onClick={runStereoisomers}>
          立体異性体を列挙
        </button>
        <button className={btn} disabled={busy} onClick={runConformer}>
          3Dで表示
        </button>
        {currentSmiles && (
          <>
            <a className={btn} href={downloadUrl("svg")} download="structure.svg">
              SVGで保存
            </a>
            <a className={btn} href={downloadUrl("png")} download="structure.png">
              PNGで保存
            </a>
          </>
        )}
      </div>

      {message && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {message}
        </p>
      )}

      {currentSmiles && (
        <p className="text-sm break-all">
          現在のSMILES: <code className="bg-gray-100 px-1 rounded">{currentSmiles}</code>
        </p>
      )}

      {analysis && (
        <div className="border rounded bg-white px-4 py-3 text-sm">
          <p className="font-bold mb-2">解析結果</p>
          <ul className="space-y-1">
            <li>分子式: {analysis.formula}</li>
            <li>分子量: {analysis.mw}</li>
            <li>精密質量: {analysis.exact_mass}</li>
            <li className="break-all">InChIKey: {analysis.inchi_key}</li>
          </ul>
          {analysis.db_match ? (
            <p className="mt-2 bg-green-50 border border-green-200 rounded px-3 py-2">
              DBに登録があります: {analysis.db_match.name_ja ?? ""} {analysis.db_match.name_en ?? ""}
              {analysis.db_match.cas ? `（CAS: ${analysis.db_match.cas}）` : ""}
            </p>
          ) : (
            <p className="mt-2 text-gray-600">この構造はDBに未登録です。</p>
          )}
        </div>
      )}

      {isomers && isomers.length > 0 && (
        <div className="border rounded bg-white px-4 py-3">
          <p className="font-bold mb-2 text-sm">立体異性体（{isomers.length}件）</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {isomers.map((iso, i) => (
              <figure key={i} className="border rounded p-2">
                <div dangerouslySetInnerHTML={{ __html: iso.svg }} />
                <figcaption className="text-xs break-all mt-1">{iso.smiles}</figcaption>
              </figure>
            ))}
          </div>
        </div>
      )}

      <div className="border rounded bg-white px-4 py-3">
        <p className="font-bold mb-2 text-sm">
          3D表示{energy !== null ? `（最適化エネルギー: ${energy} kcal/mol）` : ""}
        </p>
        <div ref={viewerHostRef} style={{ width: "100%", height: 380, position: "relative" }} />
        {energy === null && (
          <p className="text-sm text-gray-600">「3Dで表示」を押すと、ここに立体構造が表示されます（ドラッグで回転）。</p>
        )}
      </div>
    </div>
  );
}
