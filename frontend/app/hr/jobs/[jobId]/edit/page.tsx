"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import JobForm, { JobFormValues } from "../../JobForm";

export default function EditJobPage() {
  const router = useRouter();
  const params = useParams<{ jobId: string }>();
  const [initialValues, setInitialValues] = useState<Partial<JobFormValues> | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);

  useEffect(() => {
    apiFetch(`/jobs/${params.jobId}`)
      .then((job) => {
        setStatus(job.status);
        setInitialValues({
          title: job.title,
          responsibilities: job.responsibilities,
          required_skills: job.required_skills.join(", "),
          min_experience_yrs: String(job.min_experience_yrs),
          max_experience_yrs: job.max_experience_yrs != null ? String(job.max_experience_yrs) : "",
          required_education: job.required_education || "",
          min_age: job.min_age != null ? String(job.min_age) : "",
          max_age: job.max_age != null ? String(job.max_age) : "",
          location: job.location,
          job_type: job.job_type,
        });
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load job"));
  }, [params.jobId]);

  async function toggleStatus() {
    setToggling(true);
    try {
      const nextStatus = status === "open" ? "closed" : "open";
      await apiFetch(`/jobs/${params.jobId}/status?status=${nextStatus}`, { method: "PATCH" });
      setStatus(nextStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update status");
    } finally {
      setToggling(false);
    }
  }

  if (error) return <main className="mx-auto max-w-2xl p-8 text-red-600">{error}</main>;
  if (!initialValues) return null;

  return (
    <main className="mx-auto max-w-2xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Edit job posting</h1>
        <a href="/hr" className="text-sm underline">
          Back to dashboard
        </a>
      </div>

      <div className="mb-6 flex items-center justify-between rounded-md border border-neutral-200 p-3">
        <span className="text-sm">
          Status:{" "}
          <span className={status === "open" ? "text-green-700" : "text-neutral-500"}>
            {status}
          </span>
        </span>
        <button
          onClick={toggleStatus}
          disabled={toggling}
          className="rounded-md border border-neutral-300 px-3 py-1 text-sm disabled:opacity-50"
        >
          {status === "open" ? "Close posting" : "Reopen posting"}
        </button>
      </div>

      <JobForm
        initialValues={initialValues}
        submitLabel="Save changes"
        onSubmit={async (payload) => {
          await apiFetch(`/jobs/${params.jobId}`, { method: "PUT", body: JSON.stringify(payload) });
          router.push("/hr");
        }}
      />
    </main>
  );
}
