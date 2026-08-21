import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Send } from "lucide-react";
import { predict } from "../api.js";
import Disclaimer from "../components/Disclaimer.jsx";
import { useAuth } from "../auth.jsx";

const YES_NO_FIELDS = [
  ["cycle_irregular", "Are your menstrual cycles irregular?"],
  ["weight_gain", "Recent unexplained weight gain?"],
  ["hair_growth", "Excess hair growth on face or body?"],
  ["skin_darkening", "Darkening of skin (neck / underarms)?"],
  ["hair_loss", "Hair loss or thinning on the scalp?"],
  ["pimples", "Frequent acne or pimples?"],
  ["fast_food", "Do you eat fast food frequently?"],
  ["exercise", "Do you exercise regularly?"],
  ["mood_swings", "Frequent mood swings?"],
  ["family_history", "Family history of PCOS?"],
];

const initialState = {
  name: "",
  age: 25,
  weight_kg: 60,
  height_cm: 160,
  cycle_length: 30,
  cycle_irregular: false,
  weight_gain: false,
  hair_growth: false,
  skin_darkening: false,
  hair_loss: false,
  pimples: false,
  fast_food: false,
  exercise: false,
  mood_swings: false,
  family_history: false,
};

function Toggle({ label, value, onChange }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 px-4 py-3">
      <span className="text-sm text-slate-700">{label}</span>
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
        {[
          ["No", false],
          ["Yes", true],
        ].map(([txt, val]) => (
          <button
            key={txt}
            type="button"
            onClick={() => onChange(val)}
            className={`rounded-md px-3 py-1 text-sm font-medium transition ${
              value === val
                ? "bg-white text-brand-700 shadow-sm"
                : "text-slate-500"
            }`}
          >
            {txt}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Assessment() {
  const { user } = useAuth();
  const [form, setForm] = useState({ ...initialState, name: user?.name || "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const bmi = (() => {
    const h = form.height_cm / 100;
    if (!h) return 0;
    return (form.weight_kg / (h * h)).toFixed(1);
  })();

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await predict({
        ...form,
        name: form.name.trim(),
        age: Number(form.age),
        weight_kg: Number(form.weight_kg),
        height_cm: Number(form.height_cm),
        cycle_length: Number(form.cycle_length),
      });
      navigate("/result", { state: { result: data, form, name: form.name.trim() } });
    } catch (err) {
      setError(
        err?.response?.data?.detail?.toString() ||
          "Could not reach the prediction service. Is the backend running?"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-3xl font-extrabold text-slate-900">
        PCOS Risk Assessment
      </h1>
      <p className="mt-2 text-slate-600">
        Answer honestly — your responses are only used to compute this estimate.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-8">
        <div className="card">
          <h2 className="font-semibold text-slate-800">Basic information</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="label">Name</label>
              <input
                type="text"
                className="input"
                placeholder="Your name"
                required
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Age (years)</label>
              <input
                type="number"
                min="10"
                max="70"
                required
                className="input"
                value={form.age}
                onChange={(e) => set("age", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Average cycle length (days)</label>
              <input
                type="number"
                min="15"
                max="90"
                required
                className="input"
                value={form.cycle_length}
                onChange={(e) => set("cycle_length", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Weight (kg)</label>
              <input
                type="number"
                min="25"
                max="200"
                step="0.1"
                required
                className="input"
                value={form.weight_kg}
                onChange={(e) => set("weight_kg", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Height (cm)</label>
              <input
                type="number"
                min="120"
                max="210"
                step="0.1"
                required
                className="input"
                value={form.height_cm}
                onChange={(e) => set("height_cm", e.target.value)}
              />
            </div>
          </div>
          <p className="mt-3 text-sm text-slate-500">
            Calculated BMI: <span className="font-semibold text-slate-700">{bmi}</span>
          </p>
        </div>

        <div className="card">
          <h2 className="font-semibold text-slate-800">Symptoms &amp; lifestyle</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {YES_NO_FIELDS.map(([key, label]) => (
              <Toggle
                key={key}
                label={label}
                value={form[key]}
                onChange={(v) => set(key, v)}
              />
            ))}
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <Disclaimer />

        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? (
            <>
              <Loader2 size={18} className="animate-spin" /> Analysing…
            </>
          ) : (
            <>
              <Send size={18} /> Get my result
            </>
          )}
        </button>
      </form>
    </div>
  );
}
