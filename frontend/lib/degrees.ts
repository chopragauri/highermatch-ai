// Curated degree list for dropdowns (job posting's required education, and candidate
// profile's education entries) — keeps values consistent so the backend's tier-based
// education scoring (app/matching/scoring.py EDU_TIER) reliably recognizes them.
export const DEGREE_OPTIONS = [
  "Diploma",
  "Bachelor's",
  "B.Tech",
  "B.E.",
  "B.Sc",
  "BCA",
  "BBA",
  "Master's",
  "M.Tech",
  "M.E.",
  "M.Sc",
  "MCA",
  "MBA",
  "PhD",
] as const;

// Specializations shown only for degrees where a fixed list makes sense. Degrees not
// in this map (e.g. Diploma, PhD, MBA — handled separately) fall back to a free-text
// "Field of study" input in the profile form.
export const DEGREE_SPECIALIZATIONS: Record<string, string[]> = {
  "B.Tech": [
    "Computer Science",
    "Information Technology",
    "Electronics & Communication",
    "Electrical",
    "Mechanical",
    "Civil",
    "Chemical",
    "Data Science",
    "Artificial Intelligence & Machine Learning",
  ],
  "B.E.": [
    "Computer Science",
    "Information Technology",
    "Electronics & Communication",
    "Electrical",
    "Mechanical",
    "Civil",
    "Chemical",
  ],
  "M.Tech": [
    "Computer Science",
    "Information Technology",
    "Data Science",
    "Artificial Intelligence & Machine Learning",
    "Electronics & Communication",
    "Electrical",
    "Mechanical",
    "Civil",
    "VLSI Design",
  ],
  "M.E.": [
    "Computer Science",
    "Electronics & Communication",
    "Electrical",
    "Mechanical",
    "Civil",
  ],
  "B.Sc": ["Computer Science", "Physics", "Chemistry", "Mathematics", "Statistics", "Biology"],
  "M.Sc": ["Computer Science", "Physics", "Chemistry", "Mathematics", "Statistics", "Biology"],
  MBA: ["Finance", "Marketing", "Human Resources", "Operations", "Business Analytics", "Strategy"],
};
