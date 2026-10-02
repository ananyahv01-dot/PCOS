import { CheckCircle2, Loader2, Mail, Phone, UserRound } from "lucide-react";

const ROLE_LABEL = { doctor: "Doctor", counselor: "Counselor" };

// Shared list of doctors/counselors with availability badges, reused on the
// result page (pick-on-the-spot) and the patient dashboard (persistent
// preference). Pass `onSelect` to make entries selectable; omit it for a
// read-only contact list.
export default function ProviderPicker({ providers, selectedId, onSelect, busyId }) {
  if (!providers?.length) {
    return <p className="text-sm text-slate-500">No providers are set up yet.</p>;
  }

  return (
    <div className="space-y-2">
      {providers.map((p) => {
        const isSelected = selectedId === p.id;
        return (
          <div
            key={p.id}
            className={`rounded-xl border p-3 ${
              isSelected ? "border-brand-300 bg-brand-50" : "border-slate-200"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2">
                <UserRound size={18} className="mt-0.5 shrink-0 text-slate-400" />
                <div>
                  <p className="font-semibold text-slate-800">
                    {p.name}{" "}
                    <span className="font-normal text-slate-400">
                      · {ROLE_LABEL[p.role] || p.role}
                    </span>
                  </p>
                  {p.specialty && <p className="text-sm text-slate-500">{p.specialty}</p>}
                  <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-500">
                    <a href={`mailto:${p.email}`} className="flex items-center gap-1 hover:underline">
                      <Mail size={13} /> {p.email}
                    </a>
                    {p.phone && (
                      <a href={`tel:${p.phone}`} className="flex items-center gap-1 hover:underline">
                        <Phone size={13} /> {p.phone}
                      </a>
                    )}
                  </div>
                </div>
              </div>
              {/* Counselors have no availability concept — only the doctor
                  can be marked unavailable. */}
              {p.role === "doctor" && (
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
                    p.available ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {p.available ? "Available" : "Unavailable"}
                </span>
              )}
            </div>

            {onSelect && (
              <button
                onClick={() => onSelect(p)}
                disabled={(p.role === "doctor" && !p.available) || busyId === p.id || isSelected}
                className={`mt-3 w-full text-sm ${isSelected ? "btn-ghost" : "btn-primary"}`}
              >
                {busyId === p.id ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : isSelected ? (
                  <>
                    <CheckCircle2 size={16} /> Selected
                  </>
                ) : (
                  "Select"
                )}
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
