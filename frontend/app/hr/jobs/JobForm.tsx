"use client";
import { useState, FormEvent } from "react";
import { JOB_TYPES } from "@/lib/format";
import { DEGREE_OPTIONS } from "@/lib/degrees";

export type JobFormValues = {
  title: string;
  responsibilities: string;
  required_skills: string;
  min_experience_yrs: string;
  max_experience_yrs: string;
  required_education: string;
  min_age: string;
  max_age: string;
  location: string;
  job_type: string;
};

const emptyValues: JobFormValues = {
  title: "",
  responsibilities: "",
  required_skills: "",
  min_experience_yrs: "0",
  max_experience_yrs: "",
  required_education: "",
  min_age: "",
  max_age: "",
  location: "",
  job_type: "full-time",
};

// Mirrors the server-side rules in schemas.JobCreateRequest. This is a convenience
// so users get instant feedback — the server validates independently and is the
// actual gate, since these checks can be bypassed entirely.
function validate(form: JobFormValues): string | null {
  if (form.title.trim().length < 2) return "Job title must be at least 2 characters.";
  if (form.responsibilities.trim().length < 20)
    return "Responsibilities must be at least 20 characters — this text feeds the AI role-relevance score.";
  if (form.required_skills.split(",").filter((s) => s.trim()).length === 0)
    return "Add at least one required skill.";
  if (!form.location.trim()) return "Location is required.";

  const minExp = Number(form.min_experience_yrs);
  const maxExp = form.max_experience_yrs ? Number(form.max_experience_yrs) : null;
  if (Number.isNaN(minExp) || minExp < 0 || minExp > 60)
    return "Minimum experience must be between 0 and 60 years.";
  if (maxExp !== null && (Number.isNaN(maxExp) || maxExp < 0 || maxExp > 60))
    return "Maximum experience must be between 0 and 60 years.";
  if (maxExp !== null && maxExp < minExp)
    return "Maximum experience cannot be less than minimum experience.";

  const minAge = form.min_age ? Number(form.min_age) : null;
  const maxAge = form.max_age ? Number(form.max_age) : null;
  if (minAge !== null && (Number.isNaN(minAge) || minAge < 16 || minAge > 100))
    return "Minimum age must be between 16 and 100.";
  if (maxAge !== null && (Number.isNaN(maxAge) || maxAge < 16 || maxAge > 100))
    return "Maximum age must be between 16 and 100.";
  if (minAge !== null && maxAge !== null && maxAge < minAge)
    return "Maximum age cannot be less than minimum age.";

  return null;
}

export default function JobForm({
  initialValues,
  onSubmit,
  submitLabel,
}: {
  initialValues?: Partial<JobFormValues>;
  onSubmit: (payload: Record<string, unknown>) => Promise<void>;
  submitLabel: string;
}) {
  const [form, setForm] = useState<JobFormValues>({ ...emptyValues, ...initialValues });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const validationError = validate(form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      await onSubmit({
        title: form.title,
        responsibilities: form.responsibilities,
        required_skills: form.required_skills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        min_experience_yrs: Number(form.min_experience_yrs) || 0,
        max_experience_yrs: form.max_experience_yrs ? Number(form.max_experience_yrs) : null,
        required_education: form.required_education || null,
        min_age: form.min_age ? Number(form.min_age) : null,
        max_age: form.max_age ? Number(form.max_age) : null,
        location: form.location,
        job_type: form.job_type,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <input
        required
        type="text"
        placeholder="Job title (e.g. Backend Engineer)"
        className="w-full rounded-md border border-neutral-300 px-3 py-2"
        value={form.title}
        onChange={(e) => setForm({ ...form, title: e.target.value })}
      />
      <textarea
        required
        rows={4}
        placeholder="Responsibilities — this text also feeds the AI role-relevance match score, so describe the actual day-to-day work"
        className="w-full rounded-md border border-neutral-300 px-3 py-2"
        value={form.responsibilities}
        onChange={(e) => setForm({ ...form, responsibilities: e.target.value })}
      />
      <div>
        <input
          required
          type="text"
          placeholder="Required skills, comma-separated (e.g. Python, FastAPI, PostgreSQL)"
          className="w-full rounded-md border border-neutral-300 px-3 py-2"
          value={form.required_skills}
          onChange={(e) => setForm({ ...form, required_skills: e.target.value })}
        />
        <p className="mt-1 text-xs text-neutral-500">
          These are matched exactly (and semantically for close synonyms) against candidate
          resumes — this is 40% of the match score, so be specific.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <input
          required
          type="number"
          min="0"
          step="0.5"
          placeholder="Min years experience"
          className="rounded-md border border-neutral-300 px-3 py-2"
          value={form.min_experience_yrs}
          onChange={(e) => setForm({ ...form, min_experience_yrs: e.target.value })}
        />
        <input
          type="number"
          min="0"
          step="0.5"
          placeholder="Max years (optional)"
          className="rounded-md border border-neutral-300 px-3 py-2"
          value={form.max_experience_yrs}
          onChange={(e) => setForm({ ...form, max_experience_yrs: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <select
          className="rounded-md border border-neutral-300 px-3 py-2"
          value={form.required_education}
          onChange={(e) => setForm({ ...form, required_education: e.target.value })}
        >
          <option value="">No education requirement</option>
          {DEGREE_OPTIONS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <select
          className="rounded-md border border-neutral-300 px-3 py-2"
          value={form.job_type}
          onChange={(e) => setForm({ ...form, job_type: e.target.value })}
        >
          {JOB_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>
      <div>
        <p className="mb-1 text-sm font-medium text-neutral-700">
          Age eligibility criteria <span className="font-normal text-neutral-400">(optional)</span>
        </p>
        <div className="grid grid-cols-2 gap-3">
          <input
            type="number"
            min="16"
            max="100"
            placeholder="Min age"
            className="rounded-md border border-neutral-300 px-3 py-2"
            value={form.min_age}
            onChange={(e) => setForm({ ...form, min_age: e.target.value })}
          />
          <input
            type="number"
            min="16"
            max="100"
            placeholder="Max age"
            className="rounded-md border border-neutral-300 px-3 py-2"
            value={form.max_age}
            onChange={(e) => setForm({ ...form, max_age: e.target.value })}
          />
        </div>
        <p className="mt-1 text-xs text-neutral-500">
          Candidates outside this range are blocked from applying. Leave blank to accept
          all ages.
        </p>
      </div>

      <input
        required
        type="text"
        placeholder="Location (e.g. Bengaluru, or 'Remote')"
        className="w-full rounded-md border border-neutral-300 px-3 py-2"
        value={form.location}
        onChange={(e) => setForm({ ...form, location: e.target.value })}
      />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-md bg-neutral-900 py-2 font-medium text-white disabled:opacity-50"
      >
        {loading ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
