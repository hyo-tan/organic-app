"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";

const Plot = dynamic(
  async () => {
    const mod = await import("react-plotly.js");
    return mod.default;
  },
  { ssr: false }
) as any;

const getApiBaseUrl = () => {
  return "https://organic-compound-api.onrender.com";
};

type IrPeak = {
  wavenumber: string;
  assignment: string;
};

type EiMsPeak = {
  mz: number;
  intensity: number;
  assignment: string;
};

type HNmrPeak = {
  shift: string;
  multiplicity: string;
  integration: string;
  assignment: string;
};

type CNmrPeak = {
  shift: string;
  assignment: string;
};

type Compound = {
  name_ja: string;
  name_en: string;
  iupac_name: string;
  cas: string;
  cid?: number | string;
  formula: string;
  mw: number;
  smiles: string;
  melting_point: string;
  boiling_point: string;
  density: string;
  state: string;
  category?: string;
  data_quality?: string;
  ir_peaks?: IrPeak[];
  ei_ms_peaks?: EiMsPeak[];
  h_nmr_peaks?: HNmrPeak[];
  c_nmr_peaks?: CNmrPeak[];
};

type SpectrumTab = "IR" | "EI-MS" | "1H NMR" | "13C NMR";

type SpectrumPoint = {
  x: number;
  y: number;
  assignment?: string;
};

type SpectrumXY = {
  type: "EI-MS" | "MS/MS" | "IR" | "1H NMR" | "13C NMR";
  source?: string;
  source_url?: string;
  x_unit: string;
  y_unit: string;
  data: SpectrumPoint[];
};

const categoryOrder = [
  "炭化水素",
  "不飽和炭化水素",
  "芳香族",
  "アルコール",
  "エーテル",
  "アルデヒド",
  "ケトン",
  "ケトン/カルボニル",
  "カルボン酸",
  "エステル",
  "アミン・窒素化合物",
  "ハロゲン化物・溶媒",
  "含硫黄・含リン化合物",
  "天然物・生体関連",
  "酸素含有化合物",
  "その他",
];

function PlotlySpectrum({ spectrum }: { spectrum: SpectrumXY }) {
  const isMS = spectrum.type === "EI-MS" || spectrum.type === "MS/MS";
  const isIR = spectrum.type === "IR";
  const isHNMR = spectrum.type === "1H NMR";
  const isCNMR = spectrum.type === "13C NMR";
  const isNMR = isHNMR || isCNMR;
  const isStickSpectrum = isMS || isCNMR;

  const sortedData = [...spectrum.data].sort((a, b) => a.x - b.x);

  const stickX: Array<number | null> = [];
  const stickY: Array<number | null> = [];

  if (isStickSpectrum) {
    sortedData.forEach((point) => {
      stickX.push(point.x, point.x, null);
      stickY.push(0, point.y, null);
    });
  }

  const importantMsAssignments = [
    "分子イオン",
    "M⁺",
    "M+",
    "トロピリウム",
    "base peak",
    "基準ピーク",
    "アシリウム",
  ];

  const msAnnotations = isMS
    ? sortedData
        .filter((point) => {
          const assignment = point.assignment || "";

          return (
            point.y >= 50 ||
            importantMsAssignments.some((word) => assignment.includes(word))
          );
        })
        .map((point, index) => ({
          x: point.x,
          y: point.y,
          text: point.assignment
            ? `m/z ${point.x}<br>${point.assignment}`
            : `m/z ${point.x}`,
          showarrow: true,
          arrowhead: 2,
          ax: index % 2 === 0 ? -25 : 25,
          ay: -45,
          font: {
            size: 11,
          },
          bgcolor: "rgba(255,255,255,0.9)",
          bordercolor: "#999",
          borderwidth: 1,
          borderpad: 3,
        }))
    : [];

  const irAnnotations = isIR
    ? sortedData
        .filter((point) => point.assignment && point.y < 90)
        .map((point, index) => ({
          x: point.x,
          y: point.y,
          text: point.assignment || "",
          showarrow: true,
          arrowhead: 2,
          ax: index % 2 === 0 ? -25 : 25,
          ay: 40,
          font: {
            size: 11,
            color: "#b91c1c",
          },
          bgcolor: "rgba(255,255,255,0.9)",
          bordercolor: "#dc2626",
          borderwidth: 1,
          borderpad: 3,
        }))
    : [];

  const plotData = isStickSpectrum
    ? [
        {
          x: stickX,
          y: stickY,
          type: "scatter",
          mode: "lines",
          line: {
            color: isMS ? "#2563eb" : "#16a34a",
            width: 2,
          },
          hovertemplate:
            `${spectrum.x_unit}: %{x}<br>` +
            `${spectrum.y_unit}: %{y}<extra></extra>`,
        },
      ]
    : [
        {
          x: sortedData.map((point) => point.x),
          y: sortedData.map((point) => point.y),
          type: "scatter",
          mode: "lines+markers",
          marker: {
            color: isIR ? "#dc2626" : "#16a34a",
            size: 5,
          },
          line: {
            color: isIR ? "#dc2626" : "#16a34a",
            width: 2,
          },
          hovertemplate:
            `${spectrum.x_unit}: %{x}<br>` +
            `${spectrum.y_unit}: %{y}<extra></extra>`,
        },
      ];

  return (
    <div className="mt-4 w-full">
      <Plot
        data={plotData as any}
        layout={
          {
            title: {
              text: spectrum.type,
            },
            xaxis: {
              title: {
                text: spectrum.x_unit,
              },
              autorange: isIR || isNMR ? "reversed" : true,
            },
            yaxis: {
              title: {
                text: spectrum.y_unit,
              },
              range: isMS || isCNMR ? [0, 120] : isIR ? [0, 100] : undefined,
            },
            annotations: [...msAnnotations, ...irAnnotations],
            autosize: true,
            height: 460,
            margin: {
              l: 70,
              r: 30,
              t: 80,
              b: 70,
            },
          } as any
        }
        style={{
          width: "100%",
          height: "460px",
        }}
        config={{
          responsive: true,
          displaylogo: false,
        }}
      />

      {isMS && sortedData.some((point) => point.assignment) && (
        <div className="mt-4">
          <h4 className="font-bold mb-2">ピーク帰属</h4>

          <ul className="list-disc pl-6 text-sm">
            {sortedData
              .filter((point) => point.assignment)
              .map((point, index) => (
                <li key={index}>
                  m/z {point.x}, 相対強度 {point.y}: {point.assignment}
                </li>
              ))}
          </ul>
        </div>
      )}

      {isIR && sortedData.some((point) => point.assignment) && (
        <div className="mt-4">
          <h4 className="font-bold mb-2">主要吸収の帰属</h4>

          <ul className="list-disc pl-6 text-sm">
            {sortedData
              .filter((point) => point.assignment)
              .map((point, index) => (
                <li key={index}>
                  {point.x} {spectrum.x_unit}: {point.assignment}
                </li>
              ))}
          </ul>
        </div>
      )}

      {spectrum.source && (
        <p className="text-sm mt-2 text-gray-600">
          出典: {spectrum.source}
          {spectrum.source_url && (
            <>
              {" "}
              <a
                href={spectrum.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline"
              >
                source
              </a>
            </>
          )}
        </p>
      )}
    </div>
  );
}

function createFallbackEiMsSpectrum(peaks: EiMsPeak[]): SpectrumXY {
  return {
    type: "EI-MS",
    source: "compounds.json",
    source_url: "",
    x_unit: "m/z",
    y_unit: "relative intensity",
    data: peaks.map((peak) => ({
      x: peak.mz,
      y: peak.intensity,
      assignment: peak.assignment,
    })),
  };
}

function CompoundCategorySection({
  allCompounds,
  sortedCategories,
  groupedCompounds,
  setQuery,
  searchByText,
}: {
  allCompounds: Compound[];
  sortedCategories: string[];
  groupedCompounds: Record<string, Compound[]>;
  setQuery: (value: string) => void;
  searchByText: (text: string) => Promise<void>;
}) {
  return (
    <section
      className="border rounded p-6 mb-8"
      style={{
        background: "linear-gradient(135deg, #bbf7d0 0%, #86efac 100%)",
        borderColor: "#22c55e",
        boxShadow: "0 12px 28px rgba(22, 163, 74, 0.18)",
      }}
    >
      <div className="mb-5">
        <p className="text-sm font-bold text-green-800 mb-1">
          Registered Compounds
        </p>

        <h2 className="text-2xl font-bold">登録済み化合物一覧</h2>

        <p className="text-sm text-gray-700 mt-2">
          現在登録済み：{allCompounds.length} 化合物。カテゴリから選ぶと、その化合物をすぐ検索できます。
        </p>
      </div>

      {allCompounds.length > 0 ? (
        <div className="space-y-5">
          {sortedCategories.map((category, index) => (
            <details
              key={category}
              open={index < 4}
              className="border rounded p-4 bg-white"
              style={{
                borderColor: "#86efac",
              }}
            >
              <summary className="font-bold cursor-pointer">
                {category}（{groupedCompounds[category].length}件）
              </summary>

              <div className="flex gap-2 flex-wrap mt-3">
                {groupedCompounds[category].map((compound) => (
                  <button
                    key={`${compound.cas}-${compound.name_en}`}
                    className="border rounded bg-gray-50 hover:bg-blue-100"
                    style={{
                      fontSize: "0.9rem",
                      padding: "0.45rem 0.7rem",
                    }}
                    onClick={() => {
                      setQuery(compound.name_ja);
                      searchByText(compound.name_ja);
                    }}
                  >
                    {compound.name_ja}
                  </button>
                ))}
              </div>
            </details>
          ))}
        </div>
      ) : (
        <p className="text-gray-700">化合物一覧を読み込み中です。</p>
      )}
    </section>
  );
}

export default function Home() {
  const resultsRef = useRef<HTMLDivElement | null>(null);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Compound[]>([]);
  const [allCompounds, setAllCompounds] = useState<Compound[]>([]);
  const [masses, setMasses] = useState<{ [key: string]: string }>({});
  const [openSpectra, setOpenSpectra] = useState<{ [key: string]: boolean }>(
    {}
  );
  const [activeTabs, setActiveTabs] = useState<{ [key: string]: SpectrumTab }>(
    {}
  );
  const [spectraData, setSpectraData] = useState<{
    [key: string]: SpectrumXY | null;
  }>({});

  useEffect(() => {
    const fetchCompounds = async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/compounds`);
        const data = await res.json();
        setAllCompounds(data);
      } catch (error) {
        console.error(error);
        setAllCompounds([]);
      }
    };

    fetchCompounds();
  }, []);

  const groupedCompounds = allCompounds.reduce((groups, compound) => {
    const category = compound.category || "その他";

    if (!groups[category]) {
      groups[category] = [];
    }

    groups[category].push(compound);

    return groups;
  }, {} as Record<string, Compound[]>);

  const sortedCategories = Object.keys(groupedCompounds).sort((a, b) => {
    const indexA = categoryOrder.indexOf(a);
    const indexB = categoryOrder.indexOf(b);

    if (indexA === -1 && indexB === -1) {
      return a.localeCompare(b, "ja");
    }

    if (indexA === -1) {
      return 1;
    }

    if (indexB === -1) {
      return -1;
    }

    return indexA - indexB;
  });

  sortedCategories.forEach((category) => {
    groupedCompounds[category].sort((a, b) =>
      a.name_ja.localeCompare(b.name_ja, "ja")
    );
  });

  const searchByText = async (text: string) => {
    if (!text.trim()) {
      setResults([]);
      return;
    }

    try {
      const res = await fetch(
        `${getApiBaseUrl()}/api/search?q=${encodeURIComponent(text)}`
      );

      const data = await res.json();
      setResults(data);

      setTimeout(() => {
        resultsRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 100);
    } catch (error) {
      console.error(error);
      setResults([]);
    }
  };

  const handleSearch = async () => {
    await searchByText(query);
  };

  const calculateMol = (massText: string, mw: number) => {
    const mass = Number(massText);

    if (!mass || mass <= 0) {
      return null;
    }

    const mol = mass / mw;
    const mmol = mol * 1000;

    return {
      mol,
      mmol,
    };
  };

  const displayValue = (value: string | number | undefined | null) => {
    if (
      value === undefined ||
      value === null ||
      value === "" ||
      value === "-" ||
      value === "unknown"
    ) {
      return "未登録";
    }

    return value;
  };

  const getStructureImageUrl = (compound: Compound) => {
    if (compound.smiles) {
      return `https://cactus.nci.nih.gov/chemical/structure/${encodeURIComponent(
        compound.smiles
      )}/image`;
    }

    if (compound.cid) {
      return `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${compound.cid}/PNG`;
    }

    return "";
  };

  const fetchSpectrum = async (
    compoundKey: string,
    cas: string,
    spectrumType: "ei-ms" | "ir" | "h-nmr" | "c-nmr"
  ) => {
    const cacheKey = `${compoundKey}-${spectrumType}`;

    if (spectraData[cacheKey] !== undefined) {
      return;
    }

    try {
      const res = await fetch(
        `${getApiBaseUrl()}/api/compounds/${encodeURIComponent(
          cas
        )}/spectra/${spectrumType}`
      );

      if (!res.ok) {
        setSpectraData((prev) => ({
          ...prev,
          [cacheKey]: null,
        }));
        return;
      }

      const data: SpectrumXY = await res.json();

      setSpectraData((prev) => ({
        ...prev,
        [cacheKey]: data,
      }));
    } catch (error) {
      console.error(error);

      setSpectraData((prev) => ({
        ...prev,
        [cacheKey]: null,
      }));
    }
  };

  const toggleSpectrum = (key: string, cas: string) => {
    setOpenSpectra((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));

    setActiveTabs((prev) => {
      if (prev[key]) {
        return prev;
      }

      return {
        ...prev,
        [key]: "IR",
      };
    });

    fetchSpectrum(key, cas, "ir");
  };

  const setActiveTab = (key: string, tab: SpectrumTab) => {
    setActiveTabs((prev) => ({
      ...prev,
      [key]: tab,
    }));
  };

  const getQualityLabel = (quality?: string) => {
    if (quality === "high") {
      return "高品質";
    }

    if (quality === "generated") {
      return "自動生成";
    }

    return "未分類";
  };

  return (
    <main
      className="p-8"
      style={{
        minHeight: "100vh",
        background:
          "linear-gradient(180deg, #f8fafc 0%, #eef2ff 45%, #f0fdf4 100%)",
      }}
    >
      <div
        style={{
          maxWidth: "1120px",
          margin: "0 auto",
          border: "2px solid #111827",
          background: "rgba(255,255,255,0.75)",
          padding: "24px",
        }}
      >
        <section
          className="border rounded p-6 mb-6"
          style={{
            background: "linear-gradient(135deg, #fed7aa 0%, #fdba74 100%)",
            borderColor: "#fb923c",
            boxShadow: "0 12px 28px rgba(249, 115, 22, 0.18)",
            textAlign: "center",
          }}
        >
          <p className="text-sm font-bold text-orange-900 mb-1">
            Organic Chemistry Tool
          </p>

          <h1
            className="font-bold"
            style={{
              fontSize: "2.4rem",
              lineHeight: 1.15,
              letterSpacing: "0.02em",
              margin: "0 auto",
            }}
          >
            有機化合物
            <br />
            スペクトル検索
          </h1>

          <p className="text-lg mt-4 text-gray-800">
            有機化合物の構造式・命名法・基本物性・主要スペクトルを学ぶための学習用検索アプリです。
          </p>
        </section>

        <section
          className="border rounded p-6 mb-8"
          style={{
            background: "linear-gradient(135deg, #a5f3fc 0%, #67e8f9 100%)",
            borderColor: "#06b6d4",
            boxShadow: "0 12px 28px rgba(6, 182, 212, 0.18)",
          }}
        >
          <div className="mb-5">
            <p className="text-sm font-bold text-cyan-900 mb-1">
              App Description
            </p>

            <h2 className="text-2xl font-bold mb-3">
              このアプリでできること
            </h2>

            <p className="text-lg text-gray-800">
              化合物名を入力するか、下の登録済み化合物一覧から選択すると、
              化合物の基本情報、構造式、物質量計算、IR、EI-MS、¹H NMR、
              ¹³C NMRを確認できます。
            </p>

            <div
              className="mt-4 border rounded p-4 bg-white"
              style={{
                borderColor: "#0891b2",
              }}
            >
              <h3 className="font-bold mb-2 text-cyan-900">利用上の注意</h3>

              <p className="text-sm text-gray-700">
                このアプリは、実験・研究・安全性判断・正式な分析結果の確認を目的としたものではありません。
                表示される物性値やスペクトルには、学習用・参考用のデータや推定データが含まれます。
                有機化合物の構造式、命名法、官能基、主要なIR・EI-MS・NMRスペクトルの特徴を理解するための
                学習支援ツールとして使用してください。
              </p>
            </div>
          </div>

          <div className="flex gap-2 flex-wrap mb-5">
            <span className="border rounded px-3 py-1 bg-white">構造式</span>
            <span className="border rounded px-3 py-1 bg-white">命名法</span>
            <span className="border rounded px-3 py-1 bg-white">物性情報</span>
            <span className="border rounded px-3 py-1 bg-white">IR</span>
            <span className="border rounded px-3 py-1 bg-white">EI-MS</span>
            <span className="border rounded px-3 py-1 bg-white">¹H NMR</span>
            <span className="border rounded px-3 py-1 bg-white">¹³C NMR</span>
            <span className="border rounded px-3 py-1 bg-white">
              登録数：{allCompounds.length} 化合物
            </span>
          </div>

          <div className="flex gap-3 flex-wrap">
            <input
              className="border p-3 text-xl"
              style={{
                flex: "1 1 360px",
                background: "white",
              }}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  handleSearch();
                }
              }}
              placeholder="例：ベンゼン、酢酸エチル、ヘプタン"
            />

            <button
              className="bg-blue-500 text-white px-6 py-2 text-xl rounded"
              onClick={handleSearch}
            >
              検索
            </button>
          </div>
        </section>

        <CompoundCategorySection
          allCompounds={allCompounds}
          sortedCategories={sortedCategories}
          groupedCompounds={groupedCompounds}
          setQuery={setQuery}
          searchByText={searchByText}
        />

        <section ref={resultsRef}>
          <div className="mb-4">
            <h2 className="text-2xl font-bold">検索結果</h2>
            <p className="text-sm text-gray-600 mt-1">
              検索または化合物一覧から選択すると、ここに詳細情報が表示されます。
            </p>
          </div>

          <div className="space-y-6">
            {results.length > 0 ? (
              results.map((compound) => {
                const key = `${compound.name_ja}-${compound.name_en}-${compound.cas}`;
                const calc = calculateMol(masses[key], compound.mw);
                const activeTab = activeTabs[key] || "IR";

                const irSpectrum = spectraData[`${key}-ir`];
                const eiMsSpectrum = spectraData[`${key}-ei-ms`];
                const hNmrSpectrum = spectraData[`${key}-h-nmr`];
                const cNmrSpectrum = spectraData[`${key}-c-nmr`];

                const structureImageUrl = getStructureImageUrl(compound);

                return (
                  <div key={key} className="border rounded p-6 bg-white">
                    <div className="flex gap-8 flex-wrap">
                      <div className="flex-1">
                        <div className="flex gap-2 flex-wrap items-center mb-3">
                          <h2 className="text-2xl font-bold">
                            {compound.name_ja}
                          </h2>

                          <span className="border rounded px-2 py-1 text-sm bg-gray-50">
                            {getQualityLabel(compound.data_quality)}
                          </span>

                          <span className="border rounded px-2 py-1 text-sm bg-gray-50">
                            {compound.category || "その他"}
                          </span>
                        </div>

                        <p className="text-lg">{compound.name_en}</p>
                        <p className="text-lg">
                          IUPAC名: {displayValue(compound.iupac_name)}
                        </p>
                        <p className="text-lg">
                          CAS番号: {displayValue(compound.cas)}
                        </p>
                        {compound.cid && (
                          <p className="text-lg">
                            PubChem CID: {compound.cid}
                          </p>
                        )}
                        <p className="text-lg">
                          分子式: {displayValue(compound.formula)}
                        </p>
                        <p className="text-lg">
                          分子量: {displayValue(compound.mw)} g/mol
                        </p>
                        <p className="text-lg">
                          SMILES: {displayValue(compound.smiles)}
                        </p>
                        <p className="text-lg">
                          融点: {displayValue(compound.melting_point)}
                        </p>
                        <p className="text-lg">
                          沸点: {displayValue(compound.boiling_point)}
                        </p>
                        <p className="text-lg">
                          密度: {displayValue(compound.density)}
                        </p>
                        <p className="text-lg">
                          状態: {displayValue(compound.state)}
                        </p>
                      </div>

                      <div>
                        <p className="text-lg font-bold mb-2">構造式</p>

                        {structureImageUrl ? (
                          <img
                            src={structureImageUrl}
                            alt={`${compound.name_ja}の構造式`}
                            className="border rounded bg-white p-2 object-contain"
                            style={{
                              width: "16rem",
                              height: "16rem",
                              maxWidth: "100%",
                            }}
                            onError={(event) => {
                              event.currentTarget.style.display = "none";
                            }}
                          />
                        ) : (
                          <p className="text-sm text-gray-600">
                            構造式データがありません。
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="mt-6 border-t pt-4">
                      <h3 className="text-lg font-bold mb-2">物質量計算</h3>

                      <input
                        className="border p-2 mr-2"
                        type="number"
                        step="0.001"
                        placeholder="質量 g"
                        value={masses[key] || ""}
                        onChange={(event) =>
                          setMasses((prev) => ({
                            ...prev,
                            [key]: event.target.value,
                          }))
                        }
                      />

                      {calc && (
                        <div className="mt-2">
                          <p>mol: {calc.mol.toFixed(6)} mol</p>
                          <p>mmol: {calc.mmol.toFixed(3)} mmol</p>
                        </div>
                      )}
                    </div>

                    <div className="mt-6 border-t pt-4">
                      <button
                        className="text-lg font-bold mb-4 text-blue-600"
                        onClick={() => toggleSpectrum(key, compound.cas)}
                      >
                        {openSpectra[key]
                          ? "▼ スペクトル情報を閉じる"
                          : "▶ スペクトル情報を表示"}
                      </button>

                      {openSpectra[key] && (
                        <div>
                          <div className="flex gap-2 mb-4 flex-wrap">
                            <button
                              className={`px-4 py-2 border rounded ${
                                activeTab === "IR"
                                  ? "bg-blue-500 text-white"
                                  : "bg-white"
                              }`}
                              onClick={() => {
                                setActiveTab(key, "IR");
                                fetchSpectrum(key, compound.cas, "ir");
                              }}
                            >
                              IR
                            </button>

                            <button
                              className={`px-4 py-2 border rounded ${
                                activeTab === "EI-MS"
                                  ? "bg-blue-500 text-white"
                                  : "bg-white"
                              }`}
                              onClick={() => {
                                setActiveTab(key, "EI-MS");
                                fetchSpectrum(key, compound.cas, "ei-ms");
                              }}
                            >
                              EI-MS
                            </button>

                            <button
                              className={`px-4 py-2 border rounded ${
                                activeTab === "1H NMR"
                                  ? "bg-blue-500 text-white"
                                  : "bg-white"
                              }`}
                              onClick={() => {
                                setActiveTab(key, "1H NMR");
                                fetchSpectrum(key, compound.cas, "h-nmr");
                              }}
                            >
                              ¹H NMR
                            </button>

                            <button
                              className={`px-4 py-2 border rounded ${
                                activeTab === "13C NMR"
                                  ? "bg-blue-500 text-white"
                                  : "bg-white"
                              }`}
                              onClick={() => {
                                setActiveTab(key, "13C NMR");
                                fetchSpectrum(key, compound.cas, "c-nmr");
                              }}
                            >
                              ¹³C NMR
                            </button>
                          </div>

                          <div className="border rounded p-4 bg-gray-50">
                            {activeTab === "IR" && (
                              <div>
                                <h3 className="font-bold mb-2">
                                  IR スペクトル
                                </h3>

                                {irSpectrum ? (
                                  <PlotlySpectrum spectrum={irSpectrum} />
                                ) : compound.ir_peaks &&
                                  compound.ir_peaks.length > 0 ? (
                                  <div>
                                    <p className="text-sm mb-2 text-gray-600">
                                      外部スペクトルJSON未取得。
                                      compounds.json内のピークデータを表示しています。
                                    </p>

                                    <ul className="list-disc pl-6">
                                      {compound.ir_peaks.map((peak, index) => (
                                        <li key={index}>
                                          {peak.wavenumber}: {peak.assignment}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                ) : (
                                  <p>IRデータは未登録です。</p>
                                )}
                              </div>
                            )}

                            {activeTab === "EI-MS" && (
                              <div>
                                <h3 className="font-bold mb-2">
                                  EI-MS スペクトル
                                </h3>

                                {eiMsSpectrum ? (
                                  <PlotlySpectrum spectrum={eiMsSpectrum} />
                                ) : compound.ei_ms_peaks &&
                                  compound.ei_ms_peaks.length > 0 ? (
                                  <div>
                                    <p className="text-sm mb-2 text-gray-600">
                                      外部スペクトルJSON未取得。
                                      compounds.json内のピークデータを表示しています。
                                    </p>

                                    <PlotlySpectrum
                                      spectrum={createFallbackEiMsSpectrum(
                                        compound.ei_ms_peaks
                                      )}
                                    />
                                  </div>
                                ) : (
                                  <p>EI-MSデータは未登録です。</p>
                                )}
                              </div>
                            )}

                            {activeTab === "1H NMR" && (
                              <div>
                                <h3 className="font-bold mb-2">
                                  ¹H NMR スペクトル
                                </h3>

                                {hNmrSpectrum ? (
                                  <PlotlySpectrum spectrum={hNmrSpectrum} />
                                ) : compound.h_nmr_peaks &&
                                  compound.h_nmr_peaks.length > 0 ? (
                                  <ul className="list-disc pl-6">
                                    {compound.h_nmr_peaks.map(
                                      (peak, index) => (
                                        <li key={index}>
                                          δ {peak.shift},{" "}
                                          {peak.multiplicity},{" "}
                                          {peak.integration}: {peak.assignment}
                                        </li>
                                      )
                                    )}
                                  </ul>
                                ) : (
                                  <p>¹H NMRデータは未登録です。</p>
                                )}
                              </div>
                            )}

                            {activeTab === "13C NMR" && (
                              <div>
                                <h3 className="font-bold mb-2">
                                  ¹³C NMR スペクトル
                                </h3>

                                {cNmrSpectrum ? (
                                  <PlotlySpectrum spectrum={cNmrSpectrum} />
                                ) : compound.c_nmr_peaks &&
                                  compound.c_nmr_peaks.length > 0 ? (
                                  <ul className="list-disc pl-6">
                                    {compound.c_nmr_peaks.map(
                                      (peak, index) => (
                                        <li key={index}>
                                          δ {peak.shift}: {peak.assignment}
                                        </li>
                                      )
                                    )}
                                  </ul>
                                ) : (
                                  <p>¹³C NMRデータは未登録です。</p>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              query && (
                <p className="text-red-500 text-xl">
                  該当する化合物が見つかりません
                </p>
              )
            )}
          </div>
        </section>
      </div>
    </main>
  );
}