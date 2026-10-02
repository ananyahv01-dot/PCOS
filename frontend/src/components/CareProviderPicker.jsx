import ProviderPicker from "./ProviderPicker.jsx";

// The doctor is always the primary contact. Counselors are only offered as
// a fallback when the doctor is currently unavailable — counselors have no
// availability concept of their own.
export default function CareProviderPicker({ providers, selectedId, onSelect, busyId }) {
  const doctor = providers?.find((p) => p.role === "doctor");
  const counselors = providers?.filter((p) => p.role === "counselor") || [];

  if (!doctor) {
    return <ProviderPicker providers={counselors} selectedId={selectedId} onSelect={onSelect} busyId={busyId} />;
  }

  if (doctor.available) {
    return <ProviderPicker providers={[doctor]} selectedId={selectedId} onSelect={onSelect} busyId={busyId} />;
  }

  return (
    <div className="space-y-3">
      <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-500">
        <span className="font-semibold text-slate-700">{doctor.name}</span> is
        currently unavailable. Choose a counselor instead:
      </p>
      <ProviderPicker providers={counselors} selectedId={selectedId} onSelect={onSelect} busyId={busyId} />
    </div>
  );
}
