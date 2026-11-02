import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
  // Ketcher の依存ライブラリ paper は、ブラウザでは使わない Node 用ファイル
  // (jsdom / canvas を require する) を内包しており、webpack がそれを解決しようとして
  // "Module not found: jsdom/..." で落ちる。ブラウザ向けビルドでは空モジュールに逃がす。
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      canvas: false,
      jsdom: false,
      acorn: false,
      "jsdom/lib/jsdom/living/generated/utils": false,
      "jsdom/lib/generated/idl/utils": false,
    };
    return config;
  },
};

export default nextConfig;
