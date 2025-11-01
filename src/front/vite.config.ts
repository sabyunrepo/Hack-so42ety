// import { defineConfig } from 'vite'
// import react from '@vitejs/plugin-react'
// import tailwindcss from '@tailwindcss/vite'

// // https://vite.dev/config/
// export default defineConfig({
//   plugins: [react(), tailwindcss()],
// })
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import fs from "fs";
import path from "path";

export default defineConfig(() => {
  const certPath = path.resolve(__dirname, "../../docker/nginx/certs");
  const keyFile = path.join(certPath, "nginx.key");
  const certFile = path.join(certPath, "nginx.crt");

  // 인증서 파일 존재 여부 및 유효성 확인
  let httpsConfig = false;

  // HTTPS 활성화 옵션 (true: HTTPS, false: HTTP)
  const enableHttps = true; // nginx 인증서 사용

  if (enableHttps && fs.existsSync(keyFile) && fs.existsSync(certFile)) {
    try {
      httpsConfig = {
        key: fs.readFileSync(keyFile),
        cert: fs.readFileSync(certFile),
      };
      console.log("✅ HTTPS enabled with nginx certificates");
    } catch (error) {
      console.warn("⚠️  Certificate read error, falling back to HTTP:", error.message);
    }
  } else {
    console.log(enableHttps ? "ℹ️  No certificates found, using HTTP" : "ℹ️  HTTP mode (HTTPS disabled)");
  }

  return {
    plugins: [react(), tailwindcss()],

    server: {
      port: 5173,
      host: true, // Docker 환경 대응
      https: httpsConfig,

      // 개발 서버 Proxy 설정 (nginx를 통한 백엔드 접근)
      proxy: {
        // TTS API 프록시 (nginx 경유)
        "/tts": {
          target: "https://localhost",
          changeOrigin: true,
          secure: false, // self-signed 인증서 허용
          configure: (proxy, options) => {
            proxy.on("proxyReq", (proxyReq, req, res) => {
              console.log("[Proxy] TTS API:", req.method, req.url);
            });
          },
        },

        // Storybook API 프록시 (nginx 경유)
        "/storybook": {
          target: "https://localhost",
          changeOrigin: true,
          secure: false, // self-signed 인증서 허용
          configure: (proxy, options) => {
            proxy.on("proxyReq", (proxyReq, req, res) => {
              console.log("[Proxy] Storybook API:", req.method, req.url);
            });
          },
        },

        // 정적 파일 프록시 (nginx)
        "/data": {
          target: "https://localhost",
          changeOrigin: true,
          secure: false, // self-signed 인증서 허용
          configure: (proxy, options) => {
            proxy.on("proxyReq", (proxyReq, req, res) => {
              console.log("[Proxy] Static File:", req.method, req.url);
            });
          },
        },
      },
    },
  };
});
