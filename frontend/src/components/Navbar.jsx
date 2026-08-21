import { Link, useLocation, useNavigate } from "react-router-dom";
import { HeartPulse, LogIn, LogOut } from "lucide-react";
import { useAuth } from "../auth.jsx";

export default function Navbar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { isAuthed, role, user, logout } = useAuth();

  const link = (to, label) => (
    <Link
      to={to}
      className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
        pathname === to
          ? "bg-brand-50 text-brand-700"
          : "text-slate-600 hover:text-brand-700 hover:bg-brand-50"
      }`}
    >
      {label}
    </Link>
  );

  const dashboardLink = () => {
    if (role === "admin") return link("/admin", "Admin");
    if (role === "doctor") return link("/doctor", "Doctor");
    if (role === "patient") return link("/patient", "My Dashboard");
    return null;
  };

  const onLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-slate-100">
      <div className="mx-auto max-w-6xl px-4 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <span className="grid place-items-center h-9 w-9 rounded-xl bg-brand-600 text-white">
            <HeartPulse size={20} />
          </span>
          <span className="font-extrabold text-lg tracking-tight text-slate-800">
            PCOS Care <span className="text-brand-600">AI</span>
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {link("/", "Home")}
          {(!isAuthed || role === "patient") && link("/assessment", "Assessment")}
          {dashboardLink()}

          {isAuthed ? (
            <div className="ml-2 flex items-center gap-2">
              <span className="hidden sm:inline text-sm text-slate-500">
                {user?.name}{" "}
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                  {role}
                </span>
              </span>
              <button
                onClick={onLogout}
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-brand-50 hover:text-brand-700"
              >
                <LogOut size={16} /> Logout
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="ml-1 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              <LogIn size={16} /> Login
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
