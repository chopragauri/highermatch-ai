"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { matchColorClasses } from "@/lib/format";
import MatchBreakdownBars from "@/components/MatchBreakdownBars";

type Applicant = {
  id: string;
  candidate_name: string;
  candidate_email: string;
  candidate_phone: string | null;
  match_score_total: number;
  match_score_breakdown: Record<string, any>;
  match_summary_text: string;
  ai_generated?: boolean;
  status: string;
};

const STATUS_OPTIONS = ["applied", "viewed", "shortlisted", "rejected"];

export default function ApplicantsPage() {
  const params = useParams<{ jobId: string }>();
  const [jobTitle, setJobTitle] = useState<string>("");
  const [applicants, setApplicants] = useState<Applicant[] | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch(`/jobs/${params.jobId}`)
      .then((job) => setJobTitle(job.title))
      .catch(() => {});
    apiFetch(`/jobs/${params.jobId}/applicants`)
      .then(setApplicants)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load applicants"));
  }, [params.jobId]);

  async function updateStatus(applicationId: string, status: string) {
    try {
      await apiFetch(`/applications/${applicationId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setApplicants((prev) =>
        prev ? prev.map((a) => (a.id === applicationId ? { ...a, status } : a)) : prev
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update status");
    }
  }

  return (
    <main className="mx-auto max-w-3xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Applicants{jobTitle ? ` — ${jobTitle}` : ""}</h1>
          <p className="text-sm text-neutral-600">Sorted by match score, highest first.</p>
        </div>
        <a href="/hr" className="text-sm underline">
          Back to dashboard
        </a>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {applicants && applicants.length === 0 && (
        <p className="text-neutral-600">No applications yet.</p>
      )}

      <div className="space-y-3">
        {applicants?.map((a) => (
          <div key={a.id} className="rounded-md border border-neutral-200 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-medium">{a.candidate_name}</p>
                <p className="text-sm text-neutral-600">
                  {a.candidate_email}
                  {a.candidate_phone ? ` · ${a.candidate_phone}` : ""}
                </p>
              </div>
              <span
                className={`whitespace-nowrap rounded-full px-3 py-1 text-sm font-semibold ${matchColorClasses(
                  a.match_score_total
                )}`}
              >
                {a.match_score_total.toFixed(0)}%
              </span>
            </div>

            <button
              onClick={() => setExpanded(expanded === a.id ? null : a.id)}
              className="mt-2 text-sm text-blue-600 underline"
            >
              {expanded === a.id ? "Hide match details" : "Show match details"}
            </button>
            {expanded === a.id && (
              <div className="mt-2 space-y-3 rounded-md bg-neutral-50 p-3">
                <p className="text-sm text-neutral-700">{a.match_summary_text}</p>
                {a.ai_generated && (
                  <p className="text-xs text-neutral-400">
                    ✨ Explanation written by AI. Scores are computed locally and are not
                    affected by it.
                  </p>
                )}
                <MatchBreakdownBars breakdown={a.match_score_breakdown} />
              </div>
            )}

            <div className="mt-3 flex items-center gap-2">
              <span className="text-sm text-neutral-600">Status:</span>
              <select
                value={a.status}
                onChange={(e) => updateStatus(a.id, e.target.value)}
                className="rounded-md border border-neutral-300 px-2 py-1 text-sm"
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
