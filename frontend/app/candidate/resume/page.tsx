"use client";
import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";

type ParsedResume = {
  id: string;
  file_name: string;
  parsed_skills: string[];
  parsed_experience_yrs: number | null;
  parsed_education: { degree: string; field?: string | null; tier?: number }[];
  parsed_certifications: string[];
};

const ALLOWED_TYPES = new Set([
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);

export default function ResumeUploadPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [resume, setResume] = useState<ParsedResume | null>(null);
  const [loadingExisting, setLoadingExisting] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justUploaded, setJustUploaded] = useState(false);

  useEffect(() => {
    apiFetch("/resumes/me")
      .then(setResume)
      .catch(() => {}) // 404 just means no resume yet — not an error state
      .finally(() => setLoadingExisting(false));
  }, []);

  async function handleFileSelected(file: File) {
    setError(null);
    setJustUploaded(false);

    if (!ALLOWED_TYPES.has(file.type)) {
      setError("Only PDF or DOCX resumes are supported.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Resume file is too large (max 5MB).");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const parsed = await apiFetch("/resumes", { method: "POST", body: formData });
      setResume(parsed);
      setJustUploaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <main className="mx-auto max-w-2xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your resume</h1>
        <a href="/candidate" className="text-sm underline">
          Back to dashboard
        </a>
      </div>

      <p className="mb-6 text-sm text-neutral-600">
        Upload a PDF or DOCX resume. We parse it locally (skills, experience, education,
        certifications) and use it to compute your match score against every job — no
        data leaves this app for AI processing.
      </p>

      <div className="mb-6 rounded-md border border-dashed border-neutral-300 p-6 text-center">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          id="resume-file-input"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileSelected(file);
          }}
        />
        <label
          htmlFor="resume-file-input"
          className="inline-block cursor-pointer rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white"
        >
          {uploading
            ? "Uploading & parsing..."
            : resume
              ? "Upload a new resume (replaces current)"
              : "Choose file"}
        </label>
        <p className="mt-2 text-xs text-neutral-500">PDF or DOCX, up to 5MB</p>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {justUploaded && (
        <p className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-800">
          Resume uploaded and parsed ✓ — match scores across all jobs now use this resume.
        </p>
      )}

      {loadingExisting && <p className="text-sm text-neutral-500">Loading...</p>}

      {resume && (
        <div className="space-y-4 rounded-md border border-neutral-200 p-4">
          <p className="text-sm text-neutral-600">
            Current file: <span className="font-medium text-neutral-900">{resume.file_name}</span>
          </p>

          <div>
            <h2 className="mb-1 text-sm font-medium text-neutral-800">Detected skills</h2>
            {resume.parsed_skills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {resume.parsed_skills.map((s) => (
                  <span key={s} className="rounded-full bg-neutral-100 px-3 py-1 text-xs">
                    {s}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">
                No skills detected — try adding a clear &quot;Skills&quot; section to your resume.
              </p>
            )}
          </div>

          <div>
            <h2 className="mb-1 text-sm font-medium text-neutral-800">Experience</h2>
            <p className="text-sm text-neutral-700">
              {resume.parsed_experience_yrs != null
                ? `${resume.parsed_experience_yrs} years detected`
                : "Not detected"}
            </p>
          </div>

          <div>
            <h2 className="mb-1 text-sm font-medium text-neutral-800">Education</h2>
            {resume.parsed_education.length > 0 ? (
              <ul className="list-inside list-disc text-sm text-neutral-700">
                {resume.parsed_education.map((e, i) => (
                  <li key={i}>
                    {e.degree}
                    {e.field ? ` in ${e.field}` : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-neutral-500">No degree detected.</p>
            )}
          </div>

          <div>
            <h2 className="mb-1 text-sm font-medium text-neutral-800">Certifications</h2>
            {resume.parsed_certifications.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {resume.parsed_certifications.map((c) => (
                  <span key={c} className="rounded-full bg-neutral-100 px-3 py-1 text-xs">
                    {c}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">None detected.</p>
            )}
          </div>

          <p className="text-xs text-neutral-500">
            This is what the AI matching engine sees — if something looks wrong, re-upload
            a clearer version of your resume rather than editing it here.
          </p>
        </div>
      )}

      {!loadingExisting && !resume && (
        <p className="text-sm text-neutral-500">
          No resume on file yet — upload one to start seeing match scores on job listings.
        </p>
      )}

      <div className="mt-6">
        <a href="/candidate/jobs" className="text-sm underline">
          {resume ? "Browse jobs with this resume →" : "Browse jobs (no resume yet)"}
        </a>
      </div>
    </main>
  );
}
