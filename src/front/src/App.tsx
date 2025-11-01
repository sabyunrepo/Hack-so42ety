import { Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import Bookshelf from "./pages/Bookshelf";
import Settings from "./pages/Settings";
import Creator from "./pages/Creator";
import Viewer from "./pages/Viewer";

function App() {
  return (
    <>
      <div className="flex-1 w-full h-full max-w-7xl mx-auto bg-orange-50">
        <Header />
        <div className="flex-1 w-full h-full max-w-7xl mx-auto ">
          <Routes>
            <Route path="/" element={<Bookshelf />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/create" element={<Creator />} />
            <Route path="/book/:bookId" element={<Viewer />} />
            <Route path="*" element={<div>404</div>} />
          </Routes>
        </div>
      </div>
    </>
  );
}

export default App;
