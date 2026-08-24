import sys
from app.parsing.pipeline import parse_resume
from app.parsing.extractors import extract_resume_data, client
import json

with open("/home/incor/.gemini/antigravity/brain/547e55ae-4ec8-4911-979d-ca84306ed89f/.user_uploaded/media_1787576467453.pdf", "rb") as f:
    from app.parsing.extract import extract_text
    raw_text = extract_text(f.read(), "application/pdf")

print("Sending request...")
try:
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": "Extract JSON from: " + raw_text[:500]}],
        response_format={"type": "json_object"}
    )
    print(response.choices[0].message.content)
except Exception as e:
    print("API ERROR:", e)
