import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function BackButton() {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate("/")}
      className="absolute left-16 bg-white rounded-full p-3.5 shadow-xl hover:scale-110 hover:bg-yellow-400 hover:text-white transition-all"
    >
      <ArrowLeft className="w-8 h-8" />
    </button>
  );
}
