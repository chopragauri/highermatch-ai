"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { DEGREE_OPTIONS, DEGREE_SPECIALIZATIONS } from "@/lib/degrees";

type EducationEntry = {
  degree: string;
  field_of_study: string;
  institution: string;
  start_year: string;
  end_year: string;
  grade: string;
};

const emptyEducation: EducationEntry = {
  degree: "",
  field_of_study: "",
  institution: "",
  start_year: "",
  end_year: "",
  grade: "",
};

export default function CandidateProfilePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    date_of_birth: "",
    gender: "",
    current_location: "",
    preferred_location: "",
    headline: "",
    total_experience_yrs: "",
  });
  const [skillsInput, setSkillsInput] = useState("");
  const [education, setEducation] = useState<EducationEntry[]>([{ ...emptyEducation }]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function updateEducation(index: number, field: keyof EducationEntry, value: string) {
    setEducation((prev) => prev.map((e, i) => (i === index ? { ...e, [field]: value } : e)));
  }

  function addEducation() {
    setEducation((prev) => [...prev, { ...emptyEducation }]);
  }

  function removeEducation(index: number) {
    setEducation((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload = {
        date_of_birth: form.date_of_birth || null,
        gender: form.gender || null,
        current_location: form.current_location,
        preferred_location: form.preferred_location || null,
        headline: form.headline || null,
        total_experience_yrs: form.total_experience_yrs ? Number(form.total_experience_yrs) : null,
        self_reported_skills: skillsInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        education: education
          .filter((e) => e.degree)
          .map((e) => ({
            degree: e.degree,
            field_of_study: e.field_of_study || null,
            institution: e.institution || null,
            start_year: e.start_year ? Number(e.start_year) : null,
            end_year: e.end_year ? Number(e.end_year) : null,
            grade: e.grade || null,
          })),
      };
      await apiFetch("/candidates/me/profile", { method: "PUT", body: JSON.stringify(payload) });
      router.push("/candidate");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="mb-2 text-2xl font-semibold">Complete your profile</h1>
      <p className="mb-6 text-sm text-neutral-600">
        This helps us calculate an accurate match score — your location and education feed
        directly into the Education/Certification (10%) and Location (5%) components of every
        job&apos;s match percentage.
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="space-y-3">
          <h2 className="font-medium text-neutral-800">Personal details</h2>
          <div className="grid grid-cols-2 gap-3">
            <input
              type="date"
              className="rounded-md border border-neutral-300 px-3 py-2"
              value={form.date_of_birth}
              onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
            />
            <select
              className="rounded-md border border-neutral-300 px-3 py-2"
              value={form.gender}
              onChange={(e) => setForm({ ...form, gender: e.target.value })}
            >
              <option value="">Gender (optional)</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
              <option value="prefer_not_to_say">Prefer not to say</option>
            </select>
          </div>
          <input
            required
            type="text"
            placeholder="Current location (e.g. Bengaluru)"
            className="w-full rounded-md border border-neutral-300 px-3 py-2"
            value={form.current_location}
            onChange={(e) => setForm({ ...form, current_location: e.target.value })}
          />
          <input
            type="text"
            placeholder="Preferred job location (or 'Remote')"
            className="w-full rounded-md border border-neutral-300 px-3 py-2"
            value={form.preferred_location}
            onChange={(e) => setForm({ ...form, preferred_location: e.target.value })}
          />
          <input
            type="text"
            placeholder="Headline (e.g. 'Backend engineer, 3 yrs experience')"
            className="w-full rounded-md border border-neutral-300 px-3 py-2"
            value={form.headline}
            onChange={(e) => setForm({ ...form, headline: e.target.value })}
          />
        </section>

        <section className="space-y-3">
          <h2 className="font-medium text-neutral-800">Experience & skills</h2>
          <input
            type="number"
            step="0.5"
            min="0"
            placeholder="Total years of experience"
            className="w-full rounded-md border border-neutral-300 px-3 py-2"
            value={form.total_experience_yrs}
            onChange={(e) => setForm({ ...form, total_experience_yrs: e.target.value })}
          />
          <input
            type="text"
            placeholder="Skills, comma-separated (e.g. Python, React, SQL)"
            className="w-full rounded-md border border-neutral-300 px-3 py-2"
            value={skillsInput}
            onChange={(e) => setSkillsInput(e.target.value)}
          />
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-neutral-800">Education</h2>
            <button type="button" onClick={addEducation} className="text-sm text-blue-600 underline">
              + Add another
            </button>
          </div>
          {education.map((entry, i) => (
            <div key={i} className="space-y-2 rounded-md border border-neutral-200 p-3">
              <div className="grid grid-cols-2 gap-2">
                <select
                  required
                  className="rounded-md border border-neutral-300 px-3 py-2"
                  value={entry.degree}
                  onChange={(e) => updateEducation(i, "degree", e.target.value)}
                >
                  <option value="">Degree</option>
                  {DEGREE_OPTIONS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
                {DEGREE_SPECIALIZATIONS[entry.degree] ? (
                  <select
                    className="rounded-md border border-neutral-300 px-3 py-2"
                    value={entry.field_of_study}
                    onChange={(e) => updateEducation(i, "field_of_study", e.target.value)}
                  >
                    <option value="">Specialization</option>
                    {DEGREE_SPECIALIZATIONS[entry.degree].map((f) => (
                      <option key={f} value={f}>
                        {f}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    placeholder="Field of study"
                    className="rounded-md border border-neutral-300 px-3 py-2"
                    value={entry.field_of_study}
                    onChange={(e) => updateEducation(i, "field_of_study", e.target.value)}
                  />
                )}
              </div>
              <input
                type="text"
                placeholder="Institution"
                className="w-full rounded-md border border-neutral-300 px-3 py-2"
                value={entry.institution}
                onChange={(e) => updateEducation(i, "institution", e.target.value)}
              />
              <div className="grid grid-cols-3 gap-2">
                <input
                  type="number"
                  placeholder="Start year"
                  className="rounded-md border border-neutral-300 px-3 py-2"
                  value={entry.start_year}
                  onChange={(e) => updateEducation(i, "start_year", e.target.value)}
                />
                <input
                  type="number"
                  placeholder="End year"
                  className="rounded-md border border-neutral-300 px-3 py-2"
                  value={entry.end_year}
                  onChange={(e) => updateEducation(i, "end_year", e.target.value)}
                />
                <input
                  type="text"
                  placeholder="Grade/CGPA"
                  className="rounded-md border border-neutral-300 px-3 py-2"
                  value={entry.grade}
                  onChange={(e) => updateEducation(i, "grade", e.target.value)}
                />
              </div>
              {education.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeEducation(i)}
                  className="text-xs text-red-600 underline"
                >
                  Remove
                </button>
              )}
            </div>
          ))}
        </section>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-neutral-900 py-2 font-medium text-white disabled:opacity-50"
        >
          {loading ? "Saving..." : "Save profile & continue"}
        </button>
      </form>
    </main>
  );
}
