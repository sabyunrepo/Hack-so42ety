import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/use-auth";

const RequireAuth = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    // console.log("RequireAuth 에서 로그인페이지로 리다이렉트");
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

export default RequireAuth;
