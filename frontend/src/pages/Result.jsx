import { Link, useLocation, Navigate } from "react-router-dom";
import { Download, RotateCcw, Stethoscope } from "lucide-react";
import RiskGauge from "../components/RiskGauge.jsx";
import Disclaimer from "../components/Disclaimer.jsx";
import { downloadReport } from "../report.js";

const CATEGORY_STYLES = {
  Nutrition: "bg-emerald-50 text-emerald-700",
  Activity: "bg-sky-50 text-sky-700",
  Weight: "bg-amber-50 text-amber-700",
  Monitoring: "bg-violet-50 text-violet-700",
  Wellbeing: "bg-rose-50 text-rose-700",
  "Next step": "bg-brand-50 text-brand-700",
};

export default function Result() {
  const { state } = useLocation();
  const result = state?.result;
  const name = state?.name?.trim();

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
          onClick={() => downloadReport({ result, name })}
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
    </div>
  );
}
