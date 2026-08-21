import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth.jsx";

// Guards a route by authentication and (optionally) role.
export default function ProtectedRoute({ roles, children }) {
  const { isAuthed, role } = useAuth();
  const location = useLocation();

  if (!isAuthed) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (roles && !roles.includes(role)) {
    // Logged in but wrong role — send to their own home.
    const home =
      role === "admin"
        ? "/admin"
        : role === "doctor"
        ? "/doctor"
        : "/patient";
    return <Navigate to={home} replace />;
  }
  return children;
}
