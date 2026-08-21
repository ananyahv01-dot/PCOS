import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Loader2, LogIn } from "lucide-react";
import { login as apiLogin } from "../api.js";
import { useAuth } from "../auth.jsx";

const roleHome = { patient: "/patient", doctor: "/doctor", admin: "/admin" };

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiLogin(email.trim(), password);
      login(data);
      const dest = location.state?.from || roleHome[data.user.role] || "/";
      navigate(dest, { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail?.toString() || "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <div className="card">
        <div className="grid h-12 w-12 place-items-center rounded-xl bg-brand-50 text-brand-600">
          <LogIn size={24} />
        </div>
        <h1 className="mt-4 text-2xl font-extrabold text-slate-900">Log in</h1>
        <p className="mt-1 text-sm text-slate-500">
          Patients, doctors and administrators use the same login.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button className="btn-primary w-full" disabled={loading}>
            {loading ? <Loader2 size={18} className="animate-spin" /> : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-600">
          New patient?{" "}
          <Link to="/register" className="font-semibold text-brand-700">
            Create an account
          </Link>
        </p>

        <div className="mt-5 rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
          <p className="font-semibold text-slate-600">Demo accounts</p>
          <p>Doctor — doctor@pcos.ai / doctor123</p>
          <p>Admin — admin@pcos.ai / admin123</p>
        </div>
      </div>
    </div>
  );
}
