"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { jobTypeLabel, matchColorClasses } from "@/lib/format";

type SearchResult = {
  job: {
    id: string;
    title: string;
    location: string;
    job_type: string;
    min_experience_yrs: number;
    max_experience_yrs: number | null;
  };
  match: {
    total: number;
    summary: string;
    breakdown: Record<string, any>;
    age_eligible?: boolean;
    age_ineligible_reason?: string | null;
  };
};

const SORT_OPTIONS = [
  { value: "match_desc", label: "Best match" },
  { value: "newest", label: "Newest" },
  { value: "experience_asc", label: "Lowest experience required" },
];

export default function CandidateJobsPage() {
  const router = useRouter();
  const [filters, setFilters] = useState({
    role: "",
    skill: "",
    location: "",
    min_experience: "",
    max_experience: "",
  });
  const [sort, setSort] = useState("match_desc");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());

  const runSearch = useCallback(() => {
    const params = new URLSearchParams();
    if (filters.role) params.set("role", filters.role);
    if (filters.skill) params.set("skill", filters.skill);
    if (filters.location) params.set("location", filters.location);
    if (filters.min_experience) params.set("min_experience", filters.min_experience);
    if (filters.max_experience) params.set("max_experience", filters.max_experience);
    params.set("sort", sort);
    apiFetch(`/jobs/search?${params.toString()}`)
      .then(setResults)
      .catch((err) => {
        const message = err instanceof Error ? err.message : "Could not load jobs";
        if (message.toLowerCase().includes("not authenticated")) {
          router.push("/login");
        } else {
          setError(message);
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sort]);

  // Runs on mount and whenever sort changes (cheap, no typing involved). Filters need
  // an explicit Search click instead, so we're not firing a request per keystroke.
  useEffect(() => {
    runSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sort]);

  // Seed already-applied jobs from the server on load — otherwise a fresh page load
  // shows "Quick apply" for jobs the candidate already applied to in a prior session.
  useEffect(() => {
    apiFetch("/applications/me")
      .then((apps: { job_id: string }[]) => {
        setAppliedIds(new Set(apps.map((a) => a.job_id)));
      })
      .catch(() => {});
  }, []);

  async function handleApply(jobId: string) {
    setApplyingId(jobId);
    setError(null);
    try {
      await apiFetch("/applications", { method: "POST", body: JSON.stringify({ job_id: jobId }) });
      setAppliedIds((prev) => new Set(prev).add(jobId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not apply");
    } finally {
      setApplyingId(null);
    }
  }

  return (
    <main className="mx-auto max-w-3xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Browse jobs</h1>
        <a href="/candidate" className="text-sm underline">
          Back to dashboard
        </a>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
        <input
          placeholder="Role"
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm"
          value={filters.role}
          onChange={(e) => setFilters({ ...filters, role: e.target.value })}
        />
        <input
          placeholder="Skill"
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm"
          value={filters.skill}
          onChange={(e) => setFilters({ ...filters, skill: e.target.value })}
        />
        <input
          placeholder="Location"
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm"
          value={filters.location}
          onChange={(e) => setFilters({ ...filters, location: e.target.value })}
        />
        <input
          type="number"
          placeholder="Min yrs exp"
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm"
          value={filters.min_experience}
          onChange={(e) => setFilters({ ...filters, min_experience: e.target.value })}
        />
        <input
          type="number"
          placeholder="Max yrs exp"
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm"
          value={filters.max_experience}
          onChange={(e) => setFilters({ ...filters, max_experience: e.target.value })}
        />
        <select
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
      <button
        onClick={runSearch}
        className="mb-6 rounded-md bg-neutral-900 px-4 py-2 text-sm text-white"
      >
        Search
      </button>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {results && results.length === 0 && (
        <p className="text-neutral-600">No jobs match these filters.</p>
      )}

      <div className="space-y-3">
        {results?.map((r) => (
          <div key={r.job.id} className="rounded-md border border-neutral-200 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <a href={`/candidate/jobs/${r.job.id}`} className="font-medium hover:underline">
                  {r.job.title}
                </a>
                <p className="text-sm text-neutral-600">
                  {r.job.location} · {jobTypeLabel(r.job.job_type)} · {r.job.min_experience_yrs}
                  {r.job.max_experience_yrs != null ? `–${r.job.max_experience_yrs}` : "+"} yrs
                </p>
              </div>
              {r.match.total > 0 ? (
                <span
                  className={`whitespace-nowrap rounded-full px-3 py-1 text-sm font-semibold ${matchColorClasses(
                    r.match.total
                  )}`}
                >
                  {r.match.total.toFixed(0)}%
                </span>
              ) : (
                <span className="whitespace-nowrap text-xs text-neutral-500">
                  No resume on file
                </span>
              )}
            </div>
            <p className="mt-2 line-clamp-2 text-sm text-neutral-600">{r.match.summary}</p>
            {r.match.breakdown?.skills?.missing?.length > 0 && (
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-neutral-500">Missing:</span>
                {r.match.breakdown.skills.missing.slice(0, 5).map((s: string) => (
                  <span
                    key={s}
                    className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}
            <div className="mt-3 flex gap-4">
              <a href={`/candidate/jobs/${r.job.id}`} className="text-sm underline">
                View details
              </a>
              {appliedIds.has(r.job.id) ? (
                <span className="text-sm text-green-700">Applied ✓</span>
              ) : r.match.age_eligible === false ? (
                <span className="text-sm text-amber-700">Not age-eligible</span>
              ) : (
                <button
                  onClick={() => handleApply(r.job.id)}
                  disabled={applyingId === r.job.id}
                  className="text-sm text-blue-600 underline disabled:opacity-50"
                >
                  {applyingId === r.job.id ? "Applying..." : "Quick apply"}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
