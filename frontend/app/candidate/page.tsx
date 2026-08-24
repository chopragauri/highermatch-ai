"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { matchColorClasses } from "@/lib/format";

type TopMatch = {
  job: { id: string; title: string; location: string };
  match: { total: number };
};

type MyApplication = {
  id: string;
  job_id: string;
  job_title: string;
  job_location: string;
  job_status: string;
  match_score_total: number;
  status: string;
};

const STATUS_CLASSES: Record<string, string> = {
  applied: "bg-neutral-100 text-neutral-700",
  viewed: "bg-blue-100 text-blue-800",
  shortlisted: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
};

export default function CandidateDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [topMatches, setTopMatches] = useState<TopMatch[] | null>(null);
  const [applications, setApplications] = useState<MyApplication[] | null>(null);

  useEffect(() => {
    apiFetch("/auth/me")
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    apiFetch("/jobs/search?sort=match_desc")
      .then((results: TopMatch[]) => setTopMatches(results.slice(0, 5)))
      .catch(() => setTopMatches([]));
    apiFetch("/applications/me")
      .then(setApplications)
      .catch(() => setApplications([]));
  }, [user]);

  if (!user) return null;

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="mb-6 text-2xl font-semibold">Welcome, {user.full_name}</h1>
      {!user.profile_complete && (
        <p className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
          Your profile isn&apos;t complete yet.{" "}
          <a href="/candidate/profile" className="underline">
            Finish it
          </a>{" "}
          to get accurate match scores.
        </p>
      )}
      <div className="mb-8 flex gap-3">
        <a
          href="/candidate/jobs"
          className="inline-block rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white"
        >
          Browse jobs
        </a>
        <a
          href="/candidate/resume"
          className="inline-block rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium"
        >
          Manage resume
        </a>
      </div>

      <section className="mb-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-medium">Your top matches</h2>
          <a href="/candidate/jobs" className="text-sm underline">
            See all
          </a>
        </div>
        {topMatches === null && <p className="text-sm text-neutral-500">Loading...</p>}
        {topMatches && topMatches.length === 0 && (
          <p className="text-sm text-neutral-500">
            No open jobs to match against yet — check back soon.
          </p>
        )}
        <div className="space-y-2">
          {topMatches?.map((r) => (
            <a
              key={r.job.id}
              href={`/candidate/jobs/${r.job.id}`}
              className="flex items-center justify-between rounded-md border border-neutral-200 p-3 hover:bg-neutral-50"
            >
              <div>
                <p className="text-sm font-medium">{r.job.title}</p>
                <p className="text-xs text-neutral-500">{r.job.location}</p>
              </div>
              {r.match.total > 0 && (
                <span
                  className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${matchColorClasses(
                    r.match.total
                  )}`}
                >
                  {r.match.total.toFixed(0)}%
                </span>
              )}
            </a>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Your applications</h2>
        {applications === null && <p className="text-sm text-neutral-500">Loading...</p>}
        {applications && applications.length === 0 && (
          <p className="text-sm text-neutral-500">
            You haven&apos;t applied to any jobs yet.
          </p>
        )}
        <div className="space-y-2">
          {applications?.map((a) => (
            <a
              key={a.id}
              href={`/candidate/jobs/${a.job_id}`}
              className="flex items-center justify-between rounded-md border border-neutral-200 p-3 hover:bg-neutral-50"
            >
              <div>
                <p className="text-sm font-medium">{a.job_title}</p>
                <p className="text-xs text-neutral-500">
                  {a.job_location} · {a.match_score_total.toFixed(0)}% match
                  {a.job_status !== "open" ? " · posting closed" : ""}
                </p>
              </div>
              <span
                className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${
                  STATUS_CLASSES[a.status] || "bg-neutral-100 text-neutral-700"
                }`}
              >
                {a.status}
              </span>
            </a>
          ))}
        </div>
      </section>
    </main>
  );
}
