import sys
from app.parsing.pipeline import parse_resume

with open("/home/incor/.gemini/antigravity/brain/547e55ae-4ec8-4911-979d-ca84306ed89f/.user_uploaded/media_1787576467453.pdf", "rb") as f:
    file_bytes = f.read()

parsed = parse_resume(file_bytes, "application/pdf")
print("--- PARSED RESUME ---")
print("Skills:", parsed.skills)
print("Experience Yrs:", parsed.experience_yrs)
print("Education:", parsed.education)
print("Certifications:", parsed.certifications)
print("Project Keywords:", parsed.project_keywords)
