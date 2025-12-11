import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],

  server: {
    port: 5173,
    host: true,

    // 백엔드 API 프록시 설정
    proxy: {
      // API 요청은 nginx를 통해 백엔드로 전달
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      // /data는 플러그인이 직접 서빙하므로 프록시 불필요
    },
  },
});
