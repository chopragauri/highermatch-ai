"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { jobTypeLabel, matchColorClasses } from "@/lib/format";
import MatchBreakdownBars from "@/components/MatchBreakdownBars";

type Job = {
  id: string;
  title: string;
  responsibilities: string;
  required_skills: string[];
  min_experience_yrs: number;
  max_experience_yrs: number | null;
  required_education: string | null;
  location: string;
  job_type: string;
  status: string;
};

type MatchBreakdown = {
  total: number;
  breakdown: Record<string, any>;
  summary: string;
  ai_generated?: boolean;
};

export default function JobDetailPage() {
  const params = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [match, setMatch] = useState<MatchBreakdown | null>(null);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const [checkingApplied, setCheckingApplied] = useState(true);

  useEffect(() => {
    apiFetch(`/jobs/${params.jobId}`).then(setJob).catch(() => {});
    apiFetch(`/matches/${params.jobId}`)
      .then(setMatch)
      .catch((err) =>
        setMatchError(err instanceof Error ? err.message : "Could not load match score")
      );
    // Check server-side whether this job was already applied to, rather than only
    // relying on a successful apply click in the current session — otherwise a page
    // reload (or arriving via a direct link) shows a stale "Apply" button that fails
    // with a confusing 400 on click.
    apiFetch("/applications/me")
      .then((apps: { job_id: string }[]) => {
        if (apps.some((a) => a.job_id === params.jobId)) setApplied(true);
      })
      .catch(() => {})
      .finally(() => setCheckingApplied(false));
  }, [params.jobId]);

  async function handleApply() {
    setApplying(true);
    setApplyError(null);
    try {
      await apiFetch("/applications", {
        method: "POST",
        body: JSON.stringify({ job_id: params.jobId }),
      });
      setApplied(true);
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "Could not apply");
    } finally {
      setApplying(false);
    }
  }

  if (!job) return null;

  return (
    <main className="mx-auto max-w-2xl p-8">
      <a href="/candidate/jobs" className="text-sm underline">
        ← Back to search
      </a>

      <div className="my-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{job.title}</h1>
          <p className="text-sm text-neutral-600">
            {job.location} · {jobTypeLabel(job.job_type)} · {job.min_experience_yrs}
            {job.max_experience_yrs != null ? `–${job.max_experience_yrs}` : "+"} yrs
            {job.required_education ? ` · ${job.required_education}` : ""}
          </p>
        </div>
        {match && match.total > 0 && (
          <span
            className={`whitespace-nowrap rounded-full px-4 py-2 text-lg font-semibold ${matchColorClasses(
              match.total
            )}`}
          >
            {match.total.toFixed(0)}%
          </span>
        )}
      </div>

      <section className="mb-6">
        <h2 className="mb-2 font-medium text-neutral-800">Responsibilities</h2>
        <p className="whitespace-pre-line text-sm text-neutral-700">{job.responsibilities}</p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 font-medium text-neutral-800">Required skills</h2>
        <div className="flex flex-wrap gap-2">
          {job.required_skills.map((s) => (
            <span key={s} className="rounded-full bg-neutral-100 px-3 py-1 text-xs">
              {s}
            </span>
          ))}
        </div>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 font-medium text-neutral-800">Your match</h2>
        {matchError && (
          <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">{matchError}</p>
        )}
        {match && match.total > 0 && (
          <>
            <p className="mb-2 text-sm text-neutral-700">{match.summary}</p>
            {match.ai_generated && (
              <p className="mb-3 text-xs text-neutral-400">
                ✨ Explanation written by AI. Scores are computed locally and are not
                affected by it.
              </p>
            )}
            <MatchBreakdownBars breakdown={match.breakdown} />
          </>
        )}
      </section>

      {applyError && <p className="mb-3 text-sm text-red-600">{applyError}</p>}

      {checkingApplied ? null : applied ? (
        <p className="rounded-md bg-green-50 p-3 text-sm text-green-800">
          Applied successfully ✓
        </p>
      ) : (
        <button
          onClick={handleApply}
          disabled={applying || job.status !== "open"}
          className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {job.status !== "open" ? "This posting is closed" : applying ? "Applying..." : "Apply"}
        </button>
      )}
    </main>
  );
}
