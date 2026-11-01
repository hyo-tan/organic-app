// API の接続先。ローカル開発 (start_app.bat) では手元のバックエンドを使い、
// 公開環境では Render 上の API を使う。
export const getApiBaseUrl = () => {
  if (typeof window !== "undefined" && window.location.hostname === "localhost") {
    return "http://localhost:8000";
  }
  return "https://organic-compound-api.onrender.com";
};
