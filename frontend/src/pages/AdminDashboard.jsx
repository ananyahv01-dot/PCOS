import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Info, Loader2, LogOut, RefreshCw } from "lucide-react";
import { getMetrics, getStats, retrain } from "../api.js";
import { useAuth } from "../auth.jsx";

const RISK_COLORS = { Low: "#16a34a", Moderate: "#d97706", High: "#dc2626" };

// Small info icon that reveals an explanatory tooltip on hover/focus.
function InfoDot({ text }) {
  return (
    <span className="group relative inline-flex align-middle" tabIndex={0}>
      <Info size={14} className="cursor-help text-slate-400 hover:text-brand-600" />
      <span className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 w-60 -translate-x-1/2 rounded-lg bg-slate-800 px-3 py-2 text-xs font-normal leading-snug text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus:opacity-100">
        {text}
      </span>
    </span>
  );
}

function StatCard({ label, value, hint, info }) {
  return (
    <div className="card">
      <div className="flex items-center gap-1.5">
        <p className="text-sm text-slate-500">{label}</p>
        {info && <InfoDot text={info} />}
      </div>
      <p className="mt-1 text-3xl font-extrabold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { logout: authLogout } = useAuth();
  const [metrics, setMetrics] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [m, s] = await Promise.all([getMetrics(), getStats()]);
      setMetrics(m);
      setStats(s);
    } catch (err) {
      if (err?.response?.status === 401) {
        navigate("/login");
        return;
      }
      setError("Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onRetrain = async () => {
    setRetraining(true);
    try {
      await retrain();
      await load();
    } catch {
      setError("Retrain failed.");
    } finally {
      setRetraining(false);
    }
  };

  const logout = async () => {
    await authLogout();
    navigate("/login");
  };

  if (loading) {
    return (
      <div className="grid place-items-center py-32 text-slate-500">
        <Loader2 className="animate-spin" size={32} />
      </div>
    );
  }

  const cm = metrics?.confusion_matrix || [
    [0, 0],
    [0, 0],
  ];

  const riskData = stats
    ? Object.entries(stats.risk_distribution).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  const importanceData = (metrics?.feature_importance || [])
    .slice(0, 8)
    .map((f) => ({ name: f.label, importance: f.importance }));

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900">
            Admin dashboard
          </h1>
          <p className="text-sm text-slate-500">
            Random Forest model &amp; usage analytics
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={onRetrain} disabled={retraining}>
            {retraining ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <RefreshCw size={16} />
            )}
            Retrain model
          </button>
          <button className="btn-ghost" onClick={logout}>
            <LogOut size={16} /> Logout
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Model metrics */}
      <h2 className="mt-8 text-lg font-bold text-slate-800">Model performance</h2>
      <p className="text-xs text-slate-400">
        Evaluated on a held-out 20% test split ·{" "}
        {metrics?.n_samples} samples · {metrics?.n_features} features
      </p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          label="Accuracy"
          value={`${(metrics.accuracy * 100).toFixed(1)}%`}
          info="Of all test cases, the share the model classified correctly (both PCOS and non-PCOS). Overall correctness."
        />
        <StatCard
          label="Precision"
          value={`${(metrics.precision * 100).toFixed(1)}%`}
          info="When the model predicts 'PCOS risk', how often it is actually right. Higher = fewer false alarms."
        />
        <StatCard
          label="Recall"
          value={`${(metrics.recall * 100).toFixed(1)}%`}
          info="Of the people who truly have PCOS patterns, how many the model caught. Higher = fewer missed cases."
        />
        <StatCard
          label="F1-score"
          value={`${(metrics.f1 * 100).toFixed(1)}%`}
          info="A single balanced score combining precision and recall (their harmonic mean)."
        />
        <StatCard
          label="ROC-AUC"
          value={metrics.roc_auc.toFixed(3)}
          info="How well the model ranks a random PCOS case above a random non-PCOS case. 1.0 = perfect, 0.5 = random guessing."
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* Feature importance */}
        <div className="card">
          <h3 className="flex items-center gap-1.5 font-semibold text-slate-800">
            Feature importance
            <InfoDot text="How much each input influenced the model's decisions (values sum to ~1). Higher bars = more influential features." />
          </h3>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={importanceData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={150}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip />
                <Bar dataKey="importance" fill="#db2777" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Confusion matrix */}
        <div className="card">
          <h3 className="flex items-center gap-1.5 font-semibold text-slate-800">
            Confusion matrix
            <InfoDot text="Breaks test predictions into correct vs. incorrect. Diagonal (green) = correct; off-diagonal (red) = errors. Bottom-left = missed PCOS cases (false negatives)." />
          </h3>
          <div className="mt-6 grid grid-cols-[80px_1fr_1fr] gap-2 text-center text-sm">
            <div />
            <div className="font-semibold text-slate-500">Pred: No</div>
            <div className="font-semibold text-slate-500">Pred: Yes</div>

            <div className="flex items-center justify-end pr-2 font-semibold text-slate-500">
              Actual: No
            </div>
            <div className="rounded-lg bg-emerald-50 py-6 text-2xl font-bold text-emerald-700">
              {cm[0][0]}
            </div>
            <div className="rounded-lg bg-red-50 py-6 text-2xl font-bold text-red-700">
              {cm[0][1]}
            </div>

            <div className="flex items-center justify-end pr-2 font-semibold text-slate-500">
              Actual: Yes
            </div>
            <div className="rounded-lg bg-red-50 py-6 text-2xl font-bold text-red-700">
              {cm[1][0]}
            </div>
            <div className="rounded-lg bg-emerald-50 py-6 text-2xl font-bold text-emerald-700">
              {cm[1][1]}
            </div>
          </div>
          <p className="mt-4 text-xs text-slate-400">
            Green = correct predictions, red = errors.
          </p>
        </div>
      </div>

      {/* Usage stats */}
      <h2 className="mt-10 text-lg font-bold text-slate-800">Usage statistics</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Total assessments"
          value={stats.total_assessments}
          info="Total number of risk assessments users have submitted through the app."
        />
        <StatCard
          label="Average risk probability"
          value={`${(stats.average_probability * 100).toFixed(1)}%`}
          info="Mean of the model's PCOS probability across all submitted assessments."
        />
        <StatCard
          label="High-risk results"
          value={stats.risk_distribution.High}
          hint="Users advised to consult a doctor"
          info="Number of assessments classified as High risk (probability at or above 67%)."
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="font-semibold text-slate-800">Risk distribution</h3>
          <div className="mt-4 h-64">
            {stats.total_assessments === 0 ? (
              <p className="grid h-full place-items-center text-sm text-slate-400">
                No assessments recorded yet.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskData}
                    dataKey="value"
                    nameKey="name"
                    outerRadius={90}
                    label
                  >
                    {riskData.map((entry) => (
                      <Cell key={entry.name} fill={RISK_COLORS[entry.name]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="card">
          <h3 className="font-semibold text-slate-800">Recent assessments</h3>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="pb-2">Time</th>
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Age</th>
                  <th className="pb-2">BMI</th>
                  <th className="pb-2">Risk</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent.length === 0 && (
                  <tr>
                    <td colSpan="5" className="py-6 text-center text-slate-400">
                      No records yet.
                    </td>
                  </tr>
                )}
                {stats.recent.map((r, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    <td className="py-2 text-slate-500">
                      {new Date(r.created_at).toLocaleString()}
                    </td>
                    <td className="py-2 font-medium text-slate-700">
                      {r.name || "—"}
                    </td>
                    <td className="py-2">{r.age}</td>
                    <td className="py-2">{r.bmi}</td>
                    <td className="py-2">
                      <span
                        className="rounded-full px-2 py-0.5 text-xs font-semibold text-white"
                        style={{ backgroundColor: RISK_COLORS[r.risk_level] }}
                      >
                        {r.risk_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
