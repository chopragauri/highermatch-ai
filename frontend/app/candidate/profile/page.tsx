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
    tenth_percentage: "",
    twelfth_percentage: "",
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

  // Mirrors the server rules in schemas.CandidateProfileRequest. The server
  // re-validates independently — this exists so users see errors before a round-trip.
  function validate(): string | null {
    if (!form.date_of_birth) return "Date of birth is required.";
    const age = Math.floor(
      (Date.now() - new Date(form.date_of_birth).getTime()) / (365.25 * 24 * 3600 * 1000)
    );
    if (age < 16) return "You must be at least 16 years old.";
    if (age > 100) return "Please enter a valid date of birth.";

    if (!form.current_location.trim()) return "Current location is required.";
    if (!form.preferred_location.trim()) return "Preferred job location is required.";

    for (const field of ["tenth_percentage", "twelfth_percentage"] as const) {
      const label = field === "tenth_percentage" ? "Class 10" : "Class 12";
      const value = Number(form[field]);
      if (form[field] === "" || Number.isNaN(value))
        return `${label} percentage is required.`;
      if (value < 0 || value > 100) return `${label} percentage must be between 0 and 100.`;
    }

    if (form.total_experience_yrs === "" || Number.isNaN(Number(form.total_experience_yrs)))
      return "Total years of experience is required (enter 0 if you're a fresher).";
    if (Number(form.total_experience_yrs) < 0 || Number(form.total_experience_yrs) > 60)
      return "Total experience must be between 0 and 60 years.";

    if (skillsInput.split(",").filter((s) => s.trim()).length === 0)
      return "Add at least one skill.";

    const filled = education.filter((e) => e.degree);
    if (filled.length === 0) return "Add at least one education entry.";
    for (const e of filled) {
      if (!e.institution.trim()) return "Institution is required for each education entry.";
      if (!e.start_year || !e.end_year) return "Start and end year are required for each education entry.";
      if (Number(e.end_year) < Number(e.start_year))
        return "Education end year cannot be before the start year.";
    }
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      const payload = {
        date_of_birth: form.date_of_birth || null,
        gender: form.gender || null,
        current_location: form.current_location,
        preferred_location: form.preferred_location || null,
        headline: form.headline || null,
        tenth_percentage: Number(form.tenth_percentage),
        twelfth_percentage: Number(form.twelfth_percentage),
        total_experience_yrs: Number(form.total_experience_yrs),
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
        job&apos;s match percentage. All fields are required except gender and headline.
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="space-y-3">
          <h2 className="font-medium text-neutral-800">Personal details</h2>
          <div className="grid grid-cols-2 gap-3">
            <input
              required
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
            required
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
            required
            type="number"
            step="0.5"
            min="0"
            max="60"
            placeholder="Total years of experience (enter 0 if fresher)"
            className="w-full rounded-md border border-neutral-300 px-3 py-2"
            value={form.total_experience_yrs}
            onChange={(e) => setForm({ ...form, total_experience_yrs: e.target.value })}
          />
          <input
            required
            type="text"
            placeholder="Skills, comma-separated (e.g. Python, React, SQL)"
            className="w-full rounded-md border border-neutral-300 px-3 py-2"
            value={skillsInput}
            onChange={(e) => setSkillsInput(e.target.value)}
          />
        </section>

        <section className="space-y-3">
          <h2 className="font-medium text-neutral-800">Schooling</h2>
          <div className="grid grid-cols-2 gap-3">
            <input
              required
              type="number"
              step="0.01"
              min="0"
              max="100"
              placeholder="Class 10 percentage"
              className="rounded-md border border-neutral-300 px-3 py-2"
              value={form.tenth_percentage}
              onChange={(e) => setForm({ ...form, tenth_percentage: e.target.value })}
            />
            <input
              required
              type="number"
              step="0.01"
              min="0"
              max="100"
              placeholder="Class 12 percentage"
              className="rounded-md border border-neutral-300 px-3 py-2"
              value={form.twelfth_percentage}
              onChange={(e) => setForm({ ...form, twelfth_percentage: e.target.value })}
            />
          </div>
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
                required
                type="text"
                placeholder="Institution"
                className="w-full rounded-md border border-neutral-300 px-3 py-2"
                value={entry.institution}
                onChange={(e) => updateEducation(i, "institution", e.target.value)}
              />
              <div className="grid grid-cols-3 gap-2">
                <input
                  required
                  type="number"
                  placeholder="Start year"
                  className="rounded-md border border-neutral-300 px-3 py-2"
                  value={entry.start_year}
                  onChange={(e) => updateEducation(i, "start_year", e.target.value)}
                />
                <input
                  required
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
