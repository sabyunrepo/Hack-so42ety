import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import fs from "fs";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // 로컬 개발 환경: /data 폴더 직접 서빙
    {
      name: "serve-data-folder",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url?.startsWith("/data/")) {
            // data 디렉토리 절대 경로 (projectMori/data)
            const dataDir = path.resolve(__dirname, "../../data");

            // 요청된 파일 경로
            const requestPath = req.url.replace("/data/", "");
            const filePath = path.join(dataDir, requestPath);

            // 보안: Path Traversal 방지
            if (!filePath.startsWith(dataDir)) {
              res.statusCode = 403;
              res.end("Forbidden");
              return;
            }

            // 파일 존재 확인
            if (fs.existsSync(filePath)) {
              const stat = fs.statSync(filePath);

              if (stat.isFile()) {
                // MIME 타입 설정
                const ext = path.extname(filePath).toLowerCase();
                const mimeTypes: Record<string, string> = {
                  ".mp3": "audio/mpeg",
                  ".wav": "audio/wav",
                  ".ogg": "audio/ogg",
                  ".mp4": "video/mp4",
                  ".webm": "video/webm",
                  ".jpg": "image/jpeg",
                  ".jpeg": "image/jpeg",
                  ".png": "image/png",
                  ".gif": "image/gif",
                  ".svg": "image/svg+xml",
                  ".webp": "image/webp",
                  ".json": "application/json",
                  ".pdf": "application/pdf",
                  ".txt": "text/plain",
                };

                const contentType = mimeTypes[ext] || "application/octet-stream";
                res.setHeader("Content-Type", contentType);
                res.setHeader("Accept-Ranges", "bytes");

                // 파일 스트리밍 (대용량 파일 대응)
                const stream = fs.createReadStream(filePath);
                stream.on("error", () => {
                  res.statusCode = 500;
                  res.end("Internal Server Error");
                });
                stream.pipe(res);
                return;
              } else if (stat.isDirectory()) {
                // 디렉토리 접근 방지
                res.statusCode = 403;
                res.end("Directory listing not allowed");
                return;
              }
            }

            // 파일 없음
            res.statusCode = 404;
            res.end("Not Found");
            return;
          }

          // /data로 시작하지 않으면 다음 미들웨어로
          next();
        });
      },
    },
  ],

  server: {
    port: 5173,
    host: true,

    // 로컬 개발 시 로컬 백엔드 API 프록시 (Docker)
    proxy: {
      // API 전체 프록시 (백엔드로)
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      // /data는 플러그인이 직접 서빙하므로 프록시 불필요
    },
  },
});
