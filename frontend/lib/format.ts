export function matchColorClasses(score: number): string {
  if (score >= 85) return "bg-emerald-100 text-emerald-800";
  if (score >= 70) return "bg-green-100 text-green-800";
  if (score >= 55) return "bg-yellow-100 text-yellow-800";
  if (score >= 40) return "bg-orange-100 text-orange-800";
  return "bg-red-100 text-red-800";
}

export function jobTypeLabel(jobType: string): string {
  return jobType
    .split("-")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join("-");
}

export const JOB_TYPES = ["full-time", "part-time", "contract", "internship"] as const;
