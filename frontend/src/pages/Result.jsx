import { useEffect, useState } from "react";
import { Link, useLocation, Navigate } from "react-router-dom";
import { AlertTriangle, Download, Loader2, RotateCcw, Stethoscope, X } from "lucide-react";
import RiskGauge from "../components/RiskGauge.jsx";
import Disclaimer from "../components/Disclaimer.jsx";
import CareProviderPicker from "../components/CareProviderPicker.jsx";
import { downloadReport } from "../report.js";
import { getProviders, selectProvider } from "../api.js";
import { useAuth } from "../auth.jsx";

const CATEGORY_STYLES = {
  Nutrition: "bg-emerald-50 text-emerald-700",
  Activity: "bg-sky-50 text-sky-700",
  Weight: "bg-amber-50 text-amber-700",
  Monitoring: "bg-violet-50 text-violet-700",
  Wellbeing: "bg-rose-50 text-rose-700",
  "Next step": "bg-brand-50 text-brand-700",
};

// Popup urging immediate care, shown for High risk results. Lets the patient
// pick a doctor or counselor based on who's currently available; if they're
// logged in as a patient the choice is saved as their care provider.
function UrgentCareModal({ onClose }) {
  const { user, updateUser } = useAuth();
  const isPatient = user?.role === "patient";
  const [providers, setProviders] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectingId, setSelectingId] = useState(null);
  const [selectedId, setSelectedId] = useState(isPatient ? user?.preferred_provider_id : null);
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    getProviders()
      .then(setProviders)
      .catch(() => setError("Couldn't load doctor/counselor details. Please try again."))
      .finally(() => setLoading(false));
  }, []);

  const onSelect = async (provider) => {
    setError("");
    if (!isPatient) {
      // Guests have no account to save a preference against — just confirm.
      setSelectedId(provider.id);
      setConfirmed(true);
      return;
    }
    setSelectingId(provider.id);
    try {
      await selectProvider(provider.id);
      updateUser({ preferred_provider_id: provider.id });
      setSelectedId(provider.id);
      setConfirmed(true);
    } catch (err) {
      setError(err?.response?.data?.detail?.toString() || "Could not select this provider.");
    } finally {
      setSelectingId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/40 p-4">
      <div className="card w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between gap-3">
          <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-red-50 text-red-600">
            <AlertTriangle size={24} />
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={20} />
          </button>
        </div>
        <h3 className="mt-4 text-xl font-extrabold text-slate-900">
          High risk detected — please contact a doctor immediately
        </h3>
        <p className="mt-2 text-sm text-slate-600">
          Your result indicates a high probability of PCOS-related patterns.
          This is not a diagnosis, but we strongly recommend contacting your
          doctor as soon as possible — or a counselor below if the doctor
          isn't available right now.
        </p>

        {confirmed && (
          <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
            {isPatient
              ? "Saved as your care provider — reach out using their details below."
              : "Reach out using their details below. Log in or create a patient account to save this choice and share your results automatically."}
          </div>
        )}

        {error && (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-4">
          {loading ? (
            <div className="grid place-items-center py-6 text-slate-400">
              <Loader2 className="animate-spin" size={24} />
            </div>
          ) : (
            <CareProviderPicker
              providers={providers}
              selectedId={selectedId}
              onSelect={onSelect}
              busyId={selectingId}
            />
          )}
        </div>

        <button className="btn-primary mt-5 w-full" onClick={onClose}>
          I understand
        </button>
      </div>
    </div>
  );
}

export default function Result() {
  const { state } = useLocation();
  const result = state?.result;
  const name = state?.name?.trim();
  const responses = state?.form;
  const [showUrgentModal, setShowUrgentModal] = useState(false);

  useEffect(() => {
    setShowUrgentModal(result?.risk_level === "High");
  }, [result]);

  // If the user navigates here directly without a result, send them back.
  if (!result) return <Navigate to="/assessment" replace />;

  const { risk_level, probability, bmi, recommendations, disclaimer } = result;

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-extrabold text-slate-900">
          {name ? `${name}'s result` : "Your result"}
        </h1>
        <button
          className="btn-primary"
          onClick={() => downloadReport({ result, name, responses })}
        >
          <Download size={18} /> Download PDF report
        </button>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-[280px_1fr]">
        <div className="card flex flex-col items-center justify-center">
          <RiskGauge probability={probability} riskLevel={risk_level} />
          <div className="mt-4 text-center">
            <p className="text-sm text-slate-500">Your BMI</p>
            <p className="text-xl font-bold text-slate-800">{bmi}</p>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-bold text-slate-800">
            {risk_level === "High" && "Elevated risk indicators"}
            {risk_level === "Moderate" && "Some risk indicators"}
            {risk_level === "Low" && "Lower risk indicators"}
          </h2>
          <p className="mt-2 text-slate-600">
            Based on your responses, the model estimates a{" "}
            <span className="font-semibold">
              {Math.round(probability * 100)}%
            </span>{" "}
            probability associated with PCOS-related patterns. This is a
            preliminary estimate, not a diagnosis.
          </p>

          {risk_level !== "Low" && (
            <div className="mt-4 flex items-start gap-3 rounded-xl bg-brand-50 p-4 text-brand-800">
              <Stethoscope className="mt-0.5 shrink-0" size={20} />
              <p className="text-sm">
                We recommend discussing these results with a doctor or
                gynaecologist who can perform proper clinical evaluation.
              </p>
            </div>
          )}
        </div>
      </div>

      <section className="mt-8">
        <h2 className="text-xl font-bold text-slate-800">
          Personalized recommendations
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {recommendations.map((rec, i) => (
            <div key={i} className="card">
              <span
                className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  CATEGORY_STYLES[rec.category] || "bg-slate-100 text-slate-600"
                }`}
              >
                {rec.category}
              </span>
              <h3 className="mt-2 font-semibold text-slate-800">{rec.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{rec.detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <Disclaimer text={disclaimer} />
      </section>

      <div className="mt-8 flex justify-center">
        <Link to="/assessment" className="btn-ghost">
          <RotateCcw size={18} /> Take the assessment again
        </Link>
      </div>

      {showUrgentModal && (
        <UrgentCareModal onClose={() => setShowUrgentModal(false)} />
      )}
    </div>
  );
}
