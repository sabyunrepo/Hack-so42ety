import { Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import Footer from "./components/Footer";
import Bookshelf from "./pages/Bookshelf";
import Settings from "./pages/Settings";
import Creator from "./pages/Creator";
import Viewer from "./pages/Viewer";

function App() {
  return (
    <>
      <div className="flex flex-col w-full h-screen bg-orange-50 overflow-auto">
        <Header />
        <div className="flex-1 max-w-7xl mx-auto w-full ">
          <Routes>
            <Route path="/" element={<Bookshelf />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/create" element={<Creator />} />
            <Route path="/book/:bookId" element={<Viewer />} />
            <Route path="*" element={<div>404</div>} />
          </Routes>
        </div>
        <Footer />
      </div>
    </>
  );
}

export default App;
