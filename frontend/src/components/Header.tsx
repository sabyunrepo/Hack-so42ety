import { Link } from "react-router-dom";
import MoriAI_Icon from "../assets/MoriAI_Icon.svg";
import { Settings, LogOut } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

export default function Header() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="bg-[#f2bf27] relative h-[90px] flex items-center justify-center">
      <Link to="/">
        <img src={MoriAI_Icon} alt="MoriAI Logo" className="h-17 mr-2" />
      </Link>
      <div className="absolute right-7 top-1/2 -translate-y-1/2 flex items-center gap-4">
        {isAuthenticated && (
          <>
            <Link to="/settings">
              <Settings className="w-8 h-8" />
            </Link>
            <button onClick={logout} title="Logout">
              <LogOut className="w-8 h-8" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
