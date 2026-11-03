"use client";

// Phase 3: スペクトル解析ページ
// xlsx / csv を読み込んでグラフ化し、複数データの重ね描き、ピーク検出、DBとの比較ができる。
import { useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { getApiBaseUrl } from "../lib/api";

const Plot = dynamic(
  async () => {
    const mod = await import("react-plotly.js");
    return mod.default;
  },
  { ssr: false }
);

type SpectrumType = "ir" | "ei_ms" | "h_nmr" | "c_nmr";

type Series = {
  id: number;
  name: string;
  x: number[];
  y: number[];
  peaks: { x: number; y: number }[] | null;
  isDbReference?: boolean;
};

type Candidate = {
  name_ja: string | null;
  name_en: string | null;
  cas: string | null;
  formula: string | null;
  score: number;
  coverage: number;
  intensity_similarity: number | null;
  matched: { db_value: number; assignment: string; observed: number | null }[];
  missing: { db_value: number; assignment: string }[];
  total_db_peaks: number;
};

const TYPE_INFO: Record<
  SpectrumType,
  { label: string; xTitle: string; reversed: boolean; endpoint: string }
> = {
  ir: { label: "IR", xTitle: "波数 (cm⁻¹)", reversed: true, endpoint: "ir" },
  ei_ms: { label: "EI-MS", xTitle: "m/z", reversed: false, endpoint: "ei-ms" },
  h_nmr: { label: "¹H NMR", xTitle: "化学シフト (ppm)", reversed: true, endpoint: "h-nmr" },
  c_nmr: { label: "¹³C NMR", xTitle: "化学シフト (ppm)", reversed: true, endpoint: "c-nmr" },
};

const COLORS = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#65a30d"];

let nextId = 1;

export default function AnalysisPage() {
  const api = getApiBaseUrl();
  const [spectrumType, setSpectrumType] = useState<SpectrumType>("ir");
  const [invert, setInvert] = useState(true); // IR は透過率（下向きピーク）が多いので既定ON
  const [normalize, setNormalize] = useState(true);
  const [series, setSeries] = useState<Series[]>([]);
  const [compareSourceId, setCompareSourceId] = useState<number | null>(null);
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const scaleY = (s: Series): number[] => {
    if (!normalize) return s.y;
    const min = Math.min(...s.y);
    const max = Math.max(...s.y);
    const range = max - min || 1;
    return s.y.map((v) => ((v - min) / range) * 100);
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setBusy(true);
    setMessage("");
    try {
      for (const file of Array.from(files)) {
        const fd = new FormData();
        fd.append("file", file);
        const res = await fetch(`${api}/api/analysis/parse`, { method: "POST", body: fd });
        if (!res.ok) throw new Error(`${file.name}: ${res.status}`);
        const data = await res.json();
        if (!data.series || data.series.length === 0) {
          setMessage(`${file.name} から数値データ（2列）を読み取れませんでした。`);
          continue;
        }
        setSeries((prev) => [
          ...prev,
          ...data.series.map((s: { name: string; x: number[]; y: number[] }) => ({
            id: nextId++,
            name: s.name,
            x: s.x,
            y: s.y,
            peaks: null,
          })),
        ]);
      }
    } catch (e) {
      setMessage(`読み込みに失敗しました: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const detectPeaks = async (target: Series) => {
    setBusy(true);
    setMessage("");
    try {
      const res = await fetch(`${api}/api/analysis/peaks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ x: target.x, y: target.y, invert, min_prominence_ratio: 0.05 }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      setSeries((prev) =>
        prev.map((s) => (s.id === target.id ? { ...s, peaks: data.peaks } : s))
      );
      if (compareSourceId === null) setCompareSourceId(target.id);
    } catch (e) {
      setMessage(`ピーク検出に失敗しました: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(false);
    }
  };

  const runCompare = async () => {
    const source = series.find((s) => s.id === compareSourceId) ?? series.find((s) => s.peaks);
    if (!source || !source.peaks) {
      setMessage("先にいずれかのデータで「ピーク検出」を実行してください。");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const res = await fetch(`${api}/api/analysis/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          spectrum_type: spectrumType,
          peaks_x: source.peaks.map((p) => p.x),
          peaks_y: source.peaks.map((p) => p.y),
          limit: 10,
        }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      setCandidates(data.candidates);
      if (data.candidates.length === 0) {
        setMessage("DBのピークと一致する候補が見つかりませんでした。");
      }
    } catch (e) {
      setMessage(`DB比較に失敗しました: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(false);
    }
  };

  const overlayDbSpectrum = async (cand: Candidate) => {
    if (!cand.cas) return;
    setBusy(true);
    try {
      const res = await fetch(
        `${api}/api/compounds/${encodeURIComponent(cand.cas)}/spectra/${TYPE_INFO[spectrumType].endpoint}`
      );
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      const pts: { x: number; y: number }[] = data.data ?? [];
      setSeries((prev) => [
        ...prev.filter((s) => !s.isDbReference),
        {
          id: nextId++,
          name: `DB: ${cand.name_ja ?? cand.name_en ?? cand.cas}`,
          x: pts.map((p) => p.x),
          y: pts.map((p) => p.y),
          peaks: null,
          isDbReference: true,
        },
      ]);
    } catch (e) {
      setMessage(`DBスペクトルの取得に失敗しました: ${e instanceof Error ? e.message : e}`);
    } finally {
      setBusy(false);
    }
  };

  const removeSeries = (id: number) =>
    setSeries((prev) => prev.filter((s) => s.id !== id));

  const traces = series.flatMap((s, i) => {
    const color = COLORS[i % COLORS.length];
    const ys = scaleY(s);
    const base = {
      x: s.x,
      y: ys,
      type: "scatter" as const,
      mode: "lines" as const,
      name: s.name,
      line: { color, width: s.isDbReference ? 1.5 : 2, dash: s.isDbReference ? ("dash" as const) : ("solid" as const) },
    };
    if (!s.peaks) return [base];
    // ピークマーカーは正規化後の y に合わせて再計算する
    const min = Math.min(...s.y);
    const range = (Math.max(...s.y) - min) || 1;
    const marker = {
      x: s.peaks.map((p) => p.x),
      y: s.peaks.map((p) => (normalize ? ((p.y - min) / range) * 100 : p.y)),
      type: "scatter" as const,
      mode: "markers" as const,
      name: `${s.name} ピーク`,
      marker: { color, size: 8, symbol: "diamond" },
      showlegend: false,
    };
    return [base, marker];
  });

  const compareSource = series.find((s) => s.id === compareSourceId);

  const btn = "border rounded px-3 py-2 bg-white hover:bg-gray-100 disabled:opacity-50 text-sm";

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-6">
      <div className="max-w-6xl mx-auto flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">スペクトル解析</h1>
          <div className="flex gap-2">
            <Link href="/editor" className={btn}>
              構造式エディタ
            </Link>
            <Link href="/" className={btn}>
              ← 化合物検索に戻る
            </Link>
          </div>
        </div>
        <p className="text-sm text-gray-700">
          実験データ（xlsx / csv、2列： x と y）を読み込んでグラフ化し、重ね描き・ピーク検出・DBのピークとの比較ができます。
          DB比較はキュレーション済み200件のピークリストと照合します。
        </p>

        <div className="border rounded bg-white px-4 py-3 flex flex-wrap items-center gap-3 text-sm">
          <label className="font-bold">スペクトルの種類:</label>
          {(Object.keys(TYPE_INFO) as SpectrumType[]).map((t) => (
            <button
              key={t}
              className={`border rounded px-3 py-1 ${spectrumType === t ? "bg-cyan-100 font-bold" : "bg-white"}`}
              onClick={() => setSpectrumType(t)}
            >
              {TYPE_INFO[t].label}
            </button>
          ))}
          <label className="flex items-center gap-1 ml-2">
            <input type="checkbox" checked={invert} onChange={(e) => setInvert(e.target.checked)} />
            透過率モード（下向きピーク）
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={normalize} onChange={(e) => setNormalize(e.target.checked)} />
            縦軸を正規化
          </label>
        </div>

        <div className="border rounded bg-white px-4 py-3 flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,.csv,.txt"
            multiple
            onChange={(e) => handleFiles(e.target.files)}
            className="text-sm"
          />
          <span className="text-sm text-gray-600">複数ファイル・複数シートの重ね描きに対応</span>
        </div>

        {message && (
          <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{message}</p>
        )}

        {series.length > 0 && (
          <div className="border rounded bg-white px-4 py-3">
            <Plot
              data={traces}
              layout={{
                autosize: true,
                height: 460,
                margin: { l: 60, r: 20, t: 20, b: 50 },
                xaxis: {
                  title: { text: TYPE_INFO[spectrumType].xTitle },
                  autorange: TYPE_INFO[spectrumType].reversed ? ("reversed" as const) : (true as const),
                },
                yaxis: { title: { text: normalize ? "強度（正規化 0-100）" : "強度" } },
                legend: { orientation: "h" as const, y: -0.15 },
              }}
              style={{ width: "100%" }}
              config={{ responsive: true }}
            />
          </div>
        )}

        {series.length > 0 && (
          <div className="border rounded bg-white px-4 py-3 flex flex-col gap-2">
            <p className="font-bold text-sm">読み込み済みデータ</p>
            {series.map((s, i) => (
              <div key={s.id} className="flex flex-wrap items-center gap-2 text-sm border-b pb-2">
                <span className="inline-block w-3 h-3 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                <span className="font-medium">{s.name}</span>
                <span className="text-gray-500">{s.x.length} 点</span>
                {s.peaks && <span className="text-gray-700">ピーク {s.peaks.length} 件</span>}
                {!s.isDbReference && (
                  <button className={btn} disabled={busy} onClick={() => detectPeaks(s)}>
                    ピーク検出
                  </button>
                )}
                <label className="flex items-center gap-1">
                  <input
                    type="radio"
                    name="compareSource"
                    checked={compareSourceId === s.id}
                    onChange={() => setCompareSourceId(s.id)}
                  />
                  DB比較に使う
                </label>
                <button className={btn} onClick={() => removeSeries(s.id)}>
                  削除
                </button>
                {s.peaks && (
                  <span className="w-full text-xs text-gray-600 break-all">
                    {s.peaks.map((p) => p.x.toFixed(spectrumType === "ei_ms" || spectrumType === "ir" ? 0 : 2)).join(", ")}
                  </span>
                )}
              </div>
            ))}
            <div className="flex items-center gap-3 pt-1">
              <button className={btn} disabled={busy || !compareSource?.peaks} onClick={runCompare}>
                DBと比較する
              </button>
              {!compareSource?.peaks && (
                <span className="text-sm text-gray-600">比較には、対象データのピーク検出が先に必要です。</span>
              )}
            </div>
          </div>
        )}

        {candidates && candidates.length > 0 && (
          <div className="border rounded bg-white px-4 py-3 flex flex-col gap-3">
            <p className="font-bold text-sm">DB比較の候補（スコア = ピーク一致割合 × 強度の近さ）</p>
            {candidates.map((cand, i) => (
              <div key={i} className="border rounded px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-bold">
                    {i + 1}. {cand.name_ja ?? ""} {cand.name_en ?? ""}
                  </span>
                  <span className="bg-cyan-100 rounded px-2 py-0.5">スコア {cand.score.toFixed(2)}</span>
                  <span className="text-gray-600">
                    一致 {cand.matched.length} / {cand.total_db_peaks} ピーク
                  </span>
                  {cand.intensity_similarity != null && (
                    <span className="text-gray-600">
                      強度類似度 {cand.intensity_similarity.toFixed(2)}
                    </span>
                  )}
                  {cand.formula && <span className="text-gray-600">{cand.formula}</span>}
                  {cand.cas && (
                    <button className={btn} disabled={busy} onClick={() => overlayDbSpectrum(cand)}>
                      DBスペクトルを重ねる
                    </button>
                  )}
                </div>
                <p className="text-xs text-gray-700 mt-1">
                  一致:{" "}
                  {cand.matched
                    .map((m) => `${m.db_value}（${m.assignment}）`)
                    .join("、") || "なし"}
                </p>
                {cand.missing.length > 0 && (
                  <p className="text-xs text-gray-500">
                    不一致: {cand.missing.map((m) => `${m.db_value}（${m.assignment}）`).join("、")}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
