import { useState } from "react";
import { Link } from "react-router-dom";
import { KeyRound, Loader2 } from "lucide-react";
import { forgotPassword } from "../api.js";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await forgotPassword(email.trim());
      // Always show the same confirmation, whether or not the email exists.
      setSent(true);
    } catch (err) {
      setError(err?.response?.data?.detail?.toString() || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <div className="card">
        <div className="grid h-12 w-12 place-items-center rounded-xl bg-brand-50 text-brand-600">
          <KeyRound size={24} />
        </div>
        <h1 className="mt-4 text-2xl font-extrabold text-slate-900">
          Forgot password
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Enter your account email and we'll send you a reset link.
        </p>

        {sent ? (
          <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
            If an account exists for <strong>{email.trim()}</strong>, a reset
            link has been sent. Check your inbox and follow the link to
            choose a new password.
          </div>
        ) : (
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

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <button className="btn-primary w-full" disabled={loading}>
              {loading ? <Loader2 size={18} className="animate-spin" /> : "Send reset link"}
            </button>
          </form>
        )}

        <p className="mt-4 text-center text-sm text-slate-600">
          Remembered your password?{" "}
          <Link to="/login" className="font-semibold text-brand-700">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
