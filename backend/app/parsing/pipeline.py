from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np

from ..matching.embeddings import embed_text
from .extract import extract_text
from .extractors import extract_resume_data


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
    parsed_data = extract_resume_data(raw_text)
    
    return ParsedResume(
        raw_text=raw_text,
        skills=parsed_data.skills,
        experience_yrs=parsed_data.experience_yrs,
        education=[edu.model_dump() for edu in parsed_data.education],
        certifications=parsed_data.certifications,
        project_keywords=parsed_data.project_keywords,
        embedding=embed_text(raw_text),
    )

