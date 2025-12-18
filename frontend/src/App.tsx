import { Route, Routes } from "react-router-dom";
import Header from "./components/Header";
import Footer from "./components/Footer";
import Bookshelf from "./pages/Bookshelf";
import Settings from "./pages/Settings";
import Creator from "./pages/Creator";
import Viewer from "./pages/Viewer";
import LoginPage from "./pages/LoginPage";
// import RegisterPage from "./pages/RegisterPage";
import { AuthProvider } from "./components/AuthProvider";
import RequireAuth from "./components/RequireAuth";

function App() {
  return (
    <AuthProvider>
      <div className="flex flex-col w-full h-screen bg-orange-50 overflow-auto">
        <Header />
        <div className="flex-1 max-w-7xl mx-auto w-full ">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            {/* [ ]  회원가입 주석처리*/}
            {/* <Route path="/register" element={<RegisterPage />} /> */}

            <Route
              path="/"
              element={
                <RequireAuth>
                  <Bookshelf />
                </RequireAuth>
              }
            />
            <Route
              path="/settings"
              element={
                <RequireAuth>
                  <Settings />
                </RequireAuth>
              }
            />
            <Route
              path="/create"
              element={
                <RequireAuth>
                  <Creator />
                </RequireAuth>
              }
            />
            <Route
              path="/book/:bookId"
              element={
                <RequireAuth>
                  <Viewer />
                </RequireAuth>
              }
            />
            <Route path="*" element={<div>404</div>} />
          </Routes>
        </div>
        <Footer />
      </div>
    </AuthProvider>
  );
}

export default App;
