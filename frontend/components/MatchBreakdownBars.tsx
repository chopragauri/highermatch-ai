const COMPONENT_LABELS: Record<string, { label: string; weight: string }> = {
  skills: { label: "Skills", weight: "40%" },
  experience: { label: "Experience", weight: "25%" },
  role_responsibility: { label: "Role relevance", weight: "20%" },
  education: { label: "Education/Certification", weight: "10%" },
  location: { label: "Location", weight: "5%" },
};

// Shared between the candidate job-detail page and the HR applicant view, so both
// sides see the exact same weighted breakdown, not just a bare summary sentence.
export default function MatchBreakdownBars({ breakdown }: { breakdown: Record<string, any> }) {
  return (
    <div className="space-y-2">
      {Object.entries(COMPONENT_LABELS).map(([key, meta]) => {
        const component = breakdown[key];
        if (!component) return null;
        return (
          <div key={key} className="flex items-center gap-3">
            <span className="w-40 shrink-0 text-xs text-neutral-600">
              {meta.label} ({meta.weight})
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-neutral-100">
              <div
                className="h-2 rounded-full bg-neutral-900"
                style={{ width: `${Math.min(100, component.score)}%` }}
              />
            </div>
            <span className="w-10 shrink-0 text-right text-xs text-neutral-600">
              {component.score.toFixed(0)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}
