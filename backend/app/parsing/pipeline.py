from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np

from ..matching.embeddings import embed_text
from .extract import extract_text
from .extractors import (
    extract_certifications,
    extract_education,
    extract_experience_years,
    extract_project_keywords,
    extract_skills,
)


@dataclass
class ParsedResume:
    raw_text: str
    skills: List[str]
    experience_yrs: float
    education: List[Dict[str, Any]]
    certifications: List[str]
    project_keywords: List[str]
    embedding: np.ndarray


def parse_resume(file_bytes: bytes, mime: str) -> ParsedResume:
    raw_text = extract_text(file_bytes, mime)
    return ParsedResume(
        raw_text=raw_text,
        skills=extract_skills(raw_text),
        experience_yrs=extract_experience_years(raw_text),
        education=extract_education(raw_text),
        certifications=extract_certifications(raw_text),
        project_keywords=extract_project_keywords(raw_text),
        embedding=embed_text(raw_text),
    )
