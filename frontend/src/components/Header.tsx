import { Link } from "react-router-dom";
import MoriAI_Icon from "../assets/MoriAI_Icon.svg";
import { LogOut, Mic } from "lucide-react";
import { useAuth } from "../hooks/use-auth";
import LanguageSelector from "./LanguageSelector";

export default function Header() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <div className="bg-[#f2bf27] relative h-[60px] sm:h-[75px] md:h-[90px] flex items-center justify-center px-2 sm:px-4">
      <Link to="/"
      >
        <img
          src={MoriAI_Icon}
          alt="MoriAI Logo"
          className="h-12 sm:h-14 md:h-17 mr-1 sm:mr-2"
        />
      </Link>
      <div className="absolute right-2 sm:right-4 md:right-7 top-1/2 -translate-y-1/2 flex items-center gap-2 sm:gap-3 md:gap-4">
        {/* Language Selector */}
        <LanguageSelector />

        {isAuthenticated && (
          <>
            <Link to="/settings">
              <Mic className="w-6 h-6 sm:w-7 sm:h-7 md:w-8 md:h-8 text-[#3D3D3D]" />
              {/* </div> */}
            </Link>
            <button onClick={logout} title="Logout">
              <LogOut className="w-6 h-6 sm:w-7 sm:h-7 md:w-8 md:h-8 text-[#3D3D3D]" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
