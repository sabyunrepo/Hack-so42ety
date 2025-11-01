import axios from "axios";

const apiClient = axios.create({
  baseURL: "/", // 백엔드 서버 주소
  timeout: 10000, // 요청 타임아웃 (10초)
  headers: {
    "Content-Type": "application/json",
  },
});

export default apiClient;
