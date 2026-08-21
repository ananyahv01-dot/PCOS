// Simple semicircular gauge showing model probability, coloured by risk tier.
const TIERS = {
  Low: { color: "#16a34a", label: "Low risk" },
  Moderate: { color: "#d97706", label: "Moderate risk" },
  High: { color: "#dc2626", label: "High risk" },
};

export default function RiskGauge({ probability, riskLevel }) {
  const pct = Math.round(probability * 100);
  const tier = TIERS[riskLevel] || TIERS.Low;

  // Semi-circle geometry
  const radius = 90;
  const circumference = Math.PI * radius; // half circle
  const dash = (pct / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width="220" height="130" viewBox="0 0 220 130">
        <path
          d="M 20 120 A 90 90 0 0 1 200 120"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="18"
          strokeLinecap="round"
        />
        <path
          d="M 20 120 A 90 90 0 0 1 200 120"
          fill="none"
          stroke={tier.color}
          strokeWidth="18"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference}`}
        />
        <text
          x="110"
          y="105"
          textAnchor="middle"
          className="fill-slate-800"
          style={{ fontSize: 34, fontWeight: 800 }}
        >
          {pct}%
        </text>
      </svg>
      <span
        className="mt-1 rounded-full px-4 py-1 text-sm font-semibold text-white"
        style={{ backgroundColor: tier.color }}
      >
        {tier.label}
      </span>
      <p className="mt-2 text-xs text-slate-500">Model-estimated probability</p>
    </div>
  );
}
