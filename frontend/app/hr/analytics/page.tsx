"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiFetch } from "@/lib/api";

type Analytics = {
  total_jobs: number;
  open_jobs: number;
  closed_jobs: number;
  total_applicants: number;
  average_match_score: number;
  status_breakdown: Record<string, number>;
  applicants_per_job: { job_id: string; job_title: string; applicant_count: number; average_match_score: number }[];
  top_missing_skills: { skill: string; missing_count: number }[];
};

const STATUS_COLORS: Record<string, string> = {
  applied: "#a3a3a3",
  viewed: "#3b82f6",
  shortlisted: "#22c55e",
  rejected: "#ef4444",
};

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-neutral-200 p-4">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="text-sm text-neutral-500">{label}</p>
    </div>
  );
}

export default function HrAnalyticsPage() {
  const router = useRouter();
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/analytics/hr")
      .then(setData)
      .catch((err) => {
        const message = err instanceof Error ? err.message : "Could not load analytics";
        if (message.toLowerCase().includes("not authenticated")) {
          router.push("/login");
        } else {
          setError(message);
        }
      });
  }, [router]);

  if (error) return <main className="mx-auto max-w-4xl p-8 text-sm text-red-600">{error}</main>;
  if (!data) return null;

  const statusData = Object.entries(data.status_breakdown)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({ name: status, value: count }));

  return (
    <main className="mx-auto max-w-4xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <a href="/hr" className="text-sm underline">
          Back to dashboard
        </a>
      </div>

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total jobs" value={data.total_jobs} />
        <StatCard label="Open jobs" value={data.open_jobs} />
        <StatCard label="Total applicants" value={data.total_applicants} />
        <StatCard label="Avg. match score" value={`${data.average_match_score}%`} />
      </div>

      {data.total_applicants === 0 ? (
        <p className="text-sm text-neutral-500">
          No applications yet — charts will populate once candidates start applying.
        </p>
      ) : (
        <>
          <section className="mb-10 grid gap-8 sm:grid-cols-2">
            <div>
              <h2 className="mb-3 font-medium text-neutral-800">Applicant status breakdown</h2>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={statusData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={85}
                    paddingAngle={statusData.length > 1 ? 2 : 0}
                  >
                    {statusData.map((entry) => (
                      <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || "#a3a3a3"} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: any, name: any) => [value, name]} />
                  <Legend
                    formatter={(value: string) => value.charAt(0).toUpperCase() + value.slice(1)}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div>
              <h2 className="mb-3 font-medium text-neutral-800">Applicants per job</h2>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={data.applicants_per_job} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} fontSize={12} />
                  <YAxis
                    type="category"
                    dataKey="job_title"
                    width={110}
                    fontSize={12}
                    tickFormatter={(v: string) => (v.length > 14 ? v.slice(0, 14) + "…" : v)}
                  />
                  <Tooltip
                    formatter={(value: any, name: any) => [
                      value,
                      name === "applicant_count" ? "Applicants" : name,
                    ]}
                  />
                  <Bar dataKey="applicant_count" fill="#171717" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          {data.top_missing_skills.length > 0 && (
            <section>
              <h2 className="mb-1 font-medium text-neutral-800">Top skill gaps</h2>
              <p className="mb-3 text-sm text-neutral-500">
                Skills required by your postings that applicants most often lack — useful for
                spotting whether a requirement is unrealistic for your candidate pool.
              </p>
              <ResponsiveContainer width="100%" height={Math.max(160, data.top_missing_skills.length * 32)}>
                <BarChart data={data.top_missing_skills} layout="vertical" margin={{ left: 16 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} fontSize={12} />
                  <YAxis type="category" dataKey="skill" width={100} fontSize={12} />
                  <Tooltip
                    formatter={(value: any) => [value, "Candidates missing this skill"]}
                  />
                  <Bar dataKey="missing_count" fill="#ef4444" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </section>
          )}
        </>
      )}
    </main>
  );
}
