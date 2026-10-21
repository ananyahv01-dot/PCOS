import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ImagePlus, Loader2, Send, X } from "lucide-react";
import { predict, predictWithUltrasound } from "../api.js";
import { imageToDataUrl } from "../report.js";
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
  age: "",
  weight_kg: "",
  height_cm: "",
  cycle_length: "",
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

const ULTRASOUND_TYPES = ["image/png", "image/jpeg", "image/webp"];
const MAX_ULTRASOUND_BYTES = 10 * 1024 * 1024;

export default function Assessment() {
  const { user } = useAuth();
  const [form, setForm] = useState({ ...initialState, name: user?.name || "" });
  const [ultrasound, setUltrasound] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  useEffect(() => {
    if (!ultrasound) {
      setPreview("");
      return undefined;
    }
    const url = URL.createObjectURL(ultrasound);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [ultrasound]);

  const onPickUltrasound = (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!ULTRASOUND_TYPES.includes(file.type)) {
      setError("Ultrasound must be a PNG, JPEG or WebP image.");
      return;
    }
    if (file.size > MAX_ULTRASOUND_BYTES) {
      setError("Ultrasound image exceeds the 10 MB limit.");
      return;
    }
    setError("");
    setUltrasound(file);
  };

  const bmi = (() => {
    const h = Number(form.height_cm) / 100;
    if (!h || !form.weight_kg) return "—";
    return (Number(form.weight_kg) / (h * h)).toFixed(1);
  })();

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const payload = {
        ...form,
        name: form.name.trim(),
        age: Number(form.age),
        weight_kg: Number(form.weight_kg),
        height_cm: Number(form.height_cm),
        cycle_length: Number(form.cycle_length),
      };
      const data = ultrasound
        ? await predictWithUltrasound(payload, ultrasound)
        : await predict(payload);
      // A shrunk copy of the scan travels to the Result page for the report.
      const ultrasoundImage = ultrasound
        ? await imageToDataUrl(ultrasound).catch(() => "")
        : "";
      navigate("/result", {
        state: { result: data, form, name: form.name.trim(), ultrasoundImage },
      });
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
                placeholder="e.g. 28"
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
                placeholder="e.g. 30"
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
                placeholder="e.g. 65"
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
                placeholder="e.g. 160"
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

        <div className="card">
          <h2 className="font-semibold text-slate-800">
            Ovarian ultrasound <span className="font-normal text-slate-500">(optional)</span>
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            If you have a pelvic ultrasound scan, upload the image. It is
            analysed for polycystic ovarian patterns and combined with your
            answers above.
          </p>
          {ultrasound ? (
            <div className="mt-4 flex items-start gap-4 rounded-xl border border-slate-200 p-3">
              <img
                src={preview}
                alt="Ultrasound preview"
                className="h-28 w-28 shrink-0 rounded-lg bg-slate-900 object-contain"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-700">
                  {ultrasound.name}
                </p>
                <p className="text-xs text-slate-500">
                  {(ultrasound.size / 1024).toFixed(0)} KB
                </p>
              </div>
              <button
                type="button"
                onClick={() => setUltrasound(null)}
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                aria-label="Remove ultrasound image"
              >
                <X size={18} />
              </button>
            </div>
          ) : (
            <label className="mt-4 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500 transition hover:border-brand-400 hover:bg-brand-50/40">
              <ImagePlus size={28} className="text-brand-500" />
              <span>
                <span className="font-semibold text-brand-700">Choose an image</span>{" "}
                (PNG, JPEG or WebP, up to 10 MB)
              </span>
              <input
                type="file"
                accept={ULTRASOUND_TYPES.join(",")}
                className="sr-only"
                onChange={onPickUltrasound}
              />
            </label>
          )}
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
