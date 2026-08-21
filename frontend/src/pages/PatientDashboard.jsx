import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList, FileText, Loader2, Pill } from "lucide-react";
import { downloadPrescription, getHistory, getPatientPrescriptions } from "../api.js";
import { useAuth } from "../auth.jsx";

const RISK_COLORS = { Low: "#16a34a", Moderate: "#d97706", High: "#dc2626" };

export default function PatientDashboard() {
  const { user } = useAuth();
  const [history, setHistory] = useState([]);
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState(null);

  useEffect(() => {
    Promise.all([getHistory(), getPatientPrescriptions()])
      .then(([h, p]) => {
        setHistory(h.history);
        setPrescriptions(p.prescriptions);
      })
      .catch(() => setError("Could not load your dashboard."))
      .finally(() => setLoading(false));
  }, []);

  const onDownload = async (rx) => {
    setDownloadingId(rx.id);
    try {
      await downloadPrescription(rx.id, rx.filename);
    } catch {
      setError("Could not download that prescription.");
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900">
            Welcome, {user?.name?.split(" ")[0] || "there"}
          </h1>
          <p className="text-sm text-slate-500">Your PCOS assessment history</p>
        </div>
        <Link to="/assessment" className="btn-primary">
          <ClipboardList size={18} /> New assessment
        </Link>
      </div>

      <div className="card mt-8">
        <h2 className="font-semibold text-slate-800">Past assessments</h2>

        {loading ? (
          <div className="grid place-items-center py-12 text-slate-400">
            <Loader2 className="animate-spin" size={26} />
          </div>
        ) : error ? (
          <p className="py-8 text-center text-sm text-red-600">{error}</p>
        ) : history.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-slate-500">You have no assessments yet.</p>
            <Link to="/assessment" className="btn-primary mt-4">
              Take your first assessment
            </Link>
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="pb-2">Date</th>
                  <th className="pb-2">Age</th>
                  <th className="pb-2">BMI</th>
                  <th className="pb-2">Probability</th>
                  <th className="pb-2">Risk</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id} className="border-t border-slate-100">
                    <td className="py-2 text-slate-500">
                      {new Date(h.created_at).toLocaleString()}
                    </td>
                    <td className="py-2">{h.age}</td>
                    <td className="py-2">{h.bmi}</td>
                    <td className="py-2">{Math.round(h.probability * 100)}%</td>
                    <td className="py-2">
                      <span
                        className="rounded-full px-2 py-0.5 text-xs font-semibold text-white"
                        style={{ backgroundColor: RISK_COLORS[h.risk_level] }}
                      >
                        {h.risk_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card mt-6">
        <h2 className="flex items-center gap-2 font-semibold text-slate-800">
          <Pill size={18} className="text-brand-600" /> Prescriptions from your
          doctor
        </h2>

        {loading ? (
          <div className="grid place-items-center py-10 text-slate-400">
            <Loader2 className="animate-spin" size={24} />
          </div>
        ) : prescriptions.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            No prescriptions have been uploaded for you yet.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-slate-100">
            {prescriptions.map((rx) => (
              <li
                key={rx.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3"
              >
                <div className="flex items-start gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-500">
                    <FileText size={18} />
                  </span>
                  <div>
                    <p className="font-medium text-slate-800">{rx.filename}</p>
                    <p className="text-xs text-slate-500">
                      {new Date(rx.created_at).toLocaleString()}
                      {rx.doctor_name ? ` · ${rx.doctor_name}` : ""}
                    </p>
                    {rx.note && (
                      <p className="mt-1 text-sm text-slate-600">{rx.note}</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => onDownload(rx)}
                  disabled={downloadingId === rx.id}
                  className="btn-ghost text-sm"
                >
                  {downloadingId === rx.id ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <FileText size={16} />
                  )}
                  Download
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
