import { Link } from "react-router-dom";
import MoriAI_Icon from "../assets/MoriAI_Icon.svg";
import { Settings } from "lucide-react";
export default function Header() {
  return (
    <div className="bg-[#f2bf27] relative h-[90px] flex items-center justify-center">
      <Link to="/">
        <img src={MoriAI_Icon} alt="MoriAI Logo" className="h-17 mr-2" />
      </Link>
      <Link to="/settings">
        <Settings className="absolute right-7 top-1/2 -translate-y-1/2 w-8 h-8" />
      </Link>
    </div>
  );
}
