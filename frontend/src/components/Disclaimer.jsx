import { AlertTriangle } from "lucide-react";

export default function Disclaimer({ text }) {
  return (
    <div className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
      <AlertTriangle className="shrink-0 mt-0.5" size={18} />
      <p>
        {text ||
          "This tool provides a preliminary, AI-generated risk estimate only. It is not a medical diagnosis. Please consult a qualified healthcare professional."}
      </p>
    </div>
  );
}
