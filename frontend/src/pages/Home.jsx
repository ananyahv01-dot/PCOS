import { Link } from "react-router-dom";
import {
  Activity,
  ClipboardList,
  ShieldCheck,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import Disclaimer from "../components/Disclaimer.jsx";

function Feature({ icon: Icon, title, children }) {
  return (
    <div className="card">
      <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600">
        <Icon size={22} />
      </span>
      <h3 className="mt-4 font-semibold text-slate-800">{title}</h3>
      <p className="mt-1 text-sm text-slate-600">{children}</p>
    </div>
  );
}

export default function Home() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-12">
      <section className="grid gap-10 md:grid-cols-2 md:items-center">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700">
            <Sparkles size={15} /> AI-powered health awareness
          </span>
          <h1 className="mt-4 text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            Understand your{" "}
            <span className="text-brand-600">PCOS risk</span> in minutes
          </h1>
          <p className="mt-4 text-lg text-slate-600">
            PCOS Care AI analyses your health and lifestyle answers with a
            Random Forest machine-learning model to give you a preliminary risk
            estimate and personalized wellness guidance.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/assessment" className="btn-primary">
              <ClipboardList size={18} /> Start assessment
            </Link>
            <a href="#how" className="btn-ghost">
              How it works
            </a>
          </div>
          <p className="mt-4 text-sm text-slate-500">
            Free &middot; No account needed &middot; Takes ~2 minutes
          </p>
        </div>

        <div className="card bg-gradient-to-br from-brand-600 to-brand-800 text-white">
          <Stethoscope size={40} />
          <h2 className="mt-4 text-2xl font-bold">A supportive first step</h2>
          <p className="mt-2 text-brand-50">
            Early awareness of possible PCOS symptoms can encourage timely
            medical consultation. This tool helps you understand relevant risk
            factors — it never replaces a doctor.
          </p>
          <ul className="mt-4 space-y-2 text-brand-50 text-sm">
            <li className="flex items-center gap-2">
              <ShieldCheck size={16} /> Private &amp; judgement-free
            </li>
            <li className="flex items-center gap-2">
              <Activity size={16} /> Evidence-inspired lifestyle tips
            </li>
            <li className="flex items-center gap-2">
              <Sparkles size={16} /> Clear, understandable results
            </li>
          </ul>
        </div>
      </section>

      <section id="how" className="mt-16">
        <h2 className="text-2xl font-bold text-slate-800">How it works</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <Feature icon={ClipboardList} title="1. Answer questions">
            Share basic demographic, menstrual and lifestyle information through
            a short questionnaire.
          </Feature>
          <Feature icon={Activity} title="2. AI analysis">
            A trained Random Forest model evaluates your responses and estimates
            a risk level.
          </Feature>
          <Feature icon={Stethoscope} title="3. Guidance">
            Get an understandable result plus general, non-diagnostic lifestyle
            recommendations.
          </Feature>
        </div>
      </section>

      <section className="mt-12">
        <Disclaimer />
      </section>
    </div>
  );
}
