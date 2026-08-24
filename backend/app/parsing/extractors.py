import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
import os

class Education(BaseModel):
    degree: Optional[str] = Field(description="The degree name, e.g. 'Bachelor\\'s', 'Master\\'s', 'PhD'")
    field: Optional[str] = Field(description="The field of study, e.g. 'Computer Science'")
    institution: Optional[str] = Field(description="The name of the university or institution")
    tier: int = Field(description="1 for Diploma/High School, 2 for Bachelor's, 3 for Master's, 4 for PhD")

class ResumeData(BaseModel):
    skills: List[str] = Field(description="List of all technical skills and tools found in the resume")
    experience_yrs: float = Field(description="Total years of work experience, calculated from the sum of all job durations")
    education: List[Education] = Field(description="List of all education degrees")
    certifications: List[str] = Field(description="List of all certifications found")
    project_keywords: List[str] = Field(description="List of technical tools specifically used in projects")

def extract_resume_data(raw_text: str) -> ResumeData:
    try:
        api_key = os.environ.get("OPENCODE_API_KEY")
        if not api_key:
            raise ValueError("OPENCODE_API_KEY environment variable is missing or empty")
            
        base_url = os.environ.get("OPENCODE_BASE_URL", "https://opencode.ai/zen/go/v1")
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        schema = ResumeData.model_json_schema()
        prompt = f"""
You are an expert HR parser. Extract the following information from the provided resume text.
Output MUST be a valid JSON object exactly matching this JSON schema:

{json.dumps(schema, indent=2)}

Resume Text:
{raw_text}
"""
        
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output structured JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        # Some models return JSON wrapped in markdown blocks even with json_object format
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        data = json.loads(content)
        return ResumeData(**data)
        
    except Exception as e:
        print(f"Error in LLM parsing: {e}")
        # Fallback to empty data if parsing fails (prevents 500 errors)
        return ResumeData(
            skills=[],
            experience_yrs=0.0,
            education=[],
            certifications=[],
            project_keywords=[]
        )
