"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { jobTypeLabel } from "@/lib/format";

type Job = {
  id: string;
  title: string;
  location: string;
  job_type: string;
  status: string;
  created_at: string;
};

export default function HrDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/auth/me")
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    apiFetch("/jobs")
      .then(setJobs)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load jobs"));
  }, [user]);

  if (!user) return null;

  return (
    <main className="mx-auto max-w-3xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Welcome, {user.full_name}</h1>
        <a href="/hr/analytics" className="text-sm underline">
          View analytics
        </a>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-medium">Your job postings</h2>
        <a href="/hr/jobs/new" className="rounded-md bg-neutral-900 px-4 py-2 text-sm text-white">
          + New job
        </a>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {jobs && jobs.length === 0 && (
        <p className="text-neutral-600">
          No postings yet. Create your first one to start seeing candidate matches.
        </p>
      )}

      <div className="space-y-3">
        {jobs?.map((job) => (
          <div
            key={job.id}
            className="flex items-center justify-between rounded-md border border-neutral-200 p-4"
          >
            <div>
              <p className="font-medium">{job.title}</p>
              <p className="text-sm text-neutral-600">
                {job.location} · {jobTypeLabel(job.job_type)} ·{" "}
                <span className={job.status === "open" ? "text-green-700" : "text-neutral-500"}>
                  {job.status}
                </span>
              </p>
            </div>
            <div className="flex gap-3 text-sm">
              <a href={`/hr/jobs/${job.id}/applicants`} className="underline">
                Applicants
              </a>
              <a href={`/hr/jobs/${job.id}/edit`} className="underline">
                Edit
              </a>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
