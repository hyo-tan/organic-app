// API の接続先。
// - 環境変数 NEXT_PUBLIC_API_BASE_URL があれば最優先
// - ローカル開発 (start_app.bat) と自宅LAN内のミニPCサーバーでは、同じホストの 8000 番を使う
// - それ以外（公開環境）では Render 上の API を使う
export const getApiBaseUrl = () => {
  const fromEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (fromEnv) return fromEnv;
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const isPrivateLan =
      /^192\.168\./.test(host) ||
      /^10\./.test(host) ||
      /^172\.(1[6-9]|2\d|3[0-1])\./.test(host);
    if (host === "localhost" || host === "127.0.0.1" || host.endsWith(".local") || isPrivateLan) {
      return `http://${host}:8000`;
    }
  }
  return "https://organic-compound-api.onrender.com";
};
