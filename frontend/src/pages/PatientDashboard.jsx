import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ClipboardList,
  FileText,
  FlaskConical,
  Loader2,
  Pill,
  UserRound,
} from "lucide-react";
import {
  downloadBloodReport,
  downloadPrescription,
  getHistory,
  getPatientBloodReports,
  getPatientPrescriptions,
  getProviders,
  selectProvider,
  uploadBloodReport,
} from "../api.js";
import { useAuth } from "../auth.jsx";
import ProviderPicker from "../components/ProviderPicker.jsx";
import CareProviderPicker from "../components/CareProviderPicker.jsx";

const RISK_COLORS = { Low: "#16a34a", Moderate: "#d97706", High: "#dc2626" };

export default function PatientDashboard() {
  const { user, updateUser } = useAuth();
  const [history, setHistory] = useState([]);
  const [prescriptions, setPrescriptions] = useState([]);
  const [providers, setProviders] = useState([]);
  const [bloodReports, setBloodReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState(null);
  const [selectingId, setSelectingId] = useState(null);
  const [providerError, setProviderError] = useState("");
  const [bloodReportFile, setBloodReportFile] = useState(null);
  const [bloodReportNote, setBloodReportNote] = useState("");
  const [uploadingReport, setUploadingReport] = useState(false);
  const [bloodReportError, setBloodReportError] = useState("");

  const loadBloodReports = () =>
    getPatientBloodReports().then((r) => setBloodReports(r.blood_reports));

  useEffect(() => {
    Promise.all([getHistory(), getPatientPrescriptions(), getProviders(), getPatientBloodReports()])
      .then(([h, p, providersList, br]) => {
        setHistory(h.history);
        setPrescriptions(p.prescriptions);
        setProviders(providersList);
        setBloodReports(br.blood_reports);
      })
      .catch(() => setError("Could not load your dashboard."))
      .finally(() => setLoading(false));
  }, []);

  const onSelectProvider = async (provider) => {
    setSelectingId(provider.id);
    setProviderError("");
    try {
      await selectProvider(provider.id);
      updateUser({ preferred_provider_id: provider.id });
    } catch (err) {
      setProviderError(err?.response?.data?.detail?.toString() || "Could not select this provider.");
    } finally {
      setSelectingId(null);
    }
  };

  // Counselors only come into play for High-risk patients — Moderate/Low
  // stays doctor-only, with no counselor concept shown at all.
  const isHighRisk = history[0]?.risk_level === "High";
  const doctorOnly = providers.filter((p) => p.role === "doctor");

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

  const onDownloadBloodReport = async (br) => {
    setDownloadingId(`br-${br.id}`);
    try {
      await downloadBloodReport(br.id, br.filename);
    } catch {
      setError("Could not download that report.");
    } finally {
      setDownloadingId(null);
    }
  };

  const onUploadBloodReport = async (e) => {
    e.preventDefault();
    if (!bloodReportFile) return setBloodReportError("Please choose a file.");
    setUploadingReport(true);
    setBloodReportError("");
    try {
      await uploadBloodReport({ note: bloodReportNote, file: bloodReportFile });
      setBloodReportFile(null);
      setBloodReportNote("");
      await loadBloodReports();
    } catch (err) {
      setBloodReportError(err?.response?.data?.detail?.toString() || "Upload failed.");
    } finally {
      setUploadingReport(false);
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
        <h2 className="flex items-center gap-2 font-semibold text-slate-800">
          <UserRound size={18} className="text-brand-600" /> Your care provider
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          {isHighRisk
            ? "Your doctor reviews your assessments and prescriptions by default. If they're unavailable, you can choose a counselor instead."
            : "Your doctor reviews your assessments and prescriptions."}
        </p>

        {providerError && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {providerError}
          </div>
        )}

        {loading ? (
          <div className="grid place-items-center py-8 text-slate-400">
            <Loader2 className="animate-spin" size={24} />
          </div>
        ) : (
          <div className="mt-4">
            {isHighRisk ? (
              <CareProviderPicker
                providers={providers}
                selectedId={user?.preferred_provider_id}
                onSelect={onSelectProvider}
                busyId={selectingId}
              />
            ) : (
              <ProviderPicker
                providers={doctorOnly}
                selectedId={user?.preferred_provider_id}
                onSelect={onSelectProvider}
                busyId={selectingId}
              />
            )}
          </div>
        )}
      </div>

      <div className="card mt-6">
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
          provider
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
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-slate-800">{rx.filename}</p>
                      {rx.superseded ? (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">
                          Superseded by your doctor
                        </span>
                      ) : rx.provider_role === "doctor" ? (
                        <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700">
                          Current
                        </span>
                      ) : null}
                    </div>
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

      <div className="card mt-6">
        <h2 className="flex items-center gap-2 font-semibold text-slate-800">
          <FlaskConical size={18} className="text-brand-600" /> Blood / lab reports
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Share a lab report with your doctor or counselor to help them
          prescribe the right treatment.
        </p>

        {isHighRisk ? (
          <form onSubmit={onUploadBloodReport} className="mt-4 space-y-3">
            <div>
              <label className="label">Report file (PDF or image)</label>
              <input
                type="file"
                accept=".pdf,image/png,image/jpeg,image/webp"
                onChange={(e) => setBloodReportFile(e.target.files?.[0] || null)}
                className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:font-semibold file:text-brand-700 hover:file:bg-brand-100"
              />
            </div>
            <div>
              <label className="label">Note (optional)</label>
              <textarea
                className="input"
                rows={2}
                value={bloodReportNote}
                onChange={(e) => setBloodReportNote(e.target.value)}
                placeholder="e.g. Fasting insulin & lipid panel from 2 Oct"
              />
            </div>
            {bloodReportError && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {bloodReportError}
              </div>
            )}
            <button className="btn-primary" disabled={uploadingReport}>
              {uploadingReport ? <Loader2 size={18} className="animate-spin" /> : "Upload report"}
            </button>
          </form>
        ) : (
          <p className="mt-3 text-sm text-slate-500">
            Uploading a blood report is available when your latest assessment
            is High risk.
          </p>
        )}

        {bloodReports.length > 0 && (
          <ul className="mt-5 divide-y divide-slate-100">
            {bloodReports.map((br) => (
              <li
                key={br.id}
                className="flex flex-wrap items-center justify-between gap-3 py-3"
              >
                <div className="flex items-start gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-500">
                    <FlaskConical size={18} />
                  </span>
                  <div>
                    <p className="font-medium text-slate-800">{br.filename}</p>
                    <p className="text-xs text-slate-500">
                      {new Date(br.created_at).toLocaleString()}
                    </p>
                    {br.note && (
                      <p className="mt-1 text-sm text-slate-600">{br.note}</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => onDownloadBloodReport(br)}
                  disabled={downloadingId === `br-${br.id}`}
                  className="btn-ghost text-sm"
                >
                  {downloadingId === `br-${br.id}` ? (
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
