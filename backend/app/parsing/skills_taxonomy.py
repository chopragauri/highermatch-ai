"""
Curated skill taxonomy used for keyword-based extraction from resumes and for
normalizing job `required_skills`. Deliberately a flat list, not an ML model —
deterministic, fast, and easy to extend for a hackathon judge's demo domain.
"""

SKILLS_TAXONOMY = sorted({
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "html", "css",
    "bash", "shell scripting",
    # Frontend
    "react", "next.js", "vue", "angular", "svelte", "redux", "tailwind", "tailwindcss",
    "bootstrap", "webpack", "vite", "jquery",
    # Backend / frameworks
    "node.js", "express", "fastapi", "django", "flask", "spring", "spring boot",
    ".net", "asp.net", "graphql", "rest api", "grpc", "microservices",
    # Data / ML
    "machine learning", "deep learning", "nlp", "computer vision", "pandas", "numpy",
    "scikit-learn", "tensorflow", "pytorch", "keras", "data analysis", "data visualization",
    "data engineering", "etl", "spark", "hadoop", "airflow", "power bi", "tableau",
    "statistics", "a/b testing", "feature engineering", "mlops", "llm", "generative ai",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite", "oracle",
    "dynamodb", "cassandra", "database design",
    # Cloud / DevOps
    "aws", "azure", "google cloud", "gcp", "docker", "kubernetes", "terraform",
    "ansible", "ci/cd", "jenkins", "github actions", "gitlab ci", "cloud architecture",
    "linux", "networking", "security", "devops", "site reliability",
    # Mobile
    "android", "ios", "react native", "flutter",
    # Product / design
    "product management", "roadmapping", "stakeholder management", "agile", "scrum",
    "kanban", "jira", "confluence", "figma", "ui design", "ux research", "prototyping",
    "wireframing", "user research", "usability testing",
    # QA
    "selenium", "test automation", "manual testing", "cypress", "playwright",
    "unit testing", "integration testing", "postman",
    # Marketing / business (kept for realistic mismatch demo cases)
    "digital marketing", "seo", "sem", "content strategy", "google analytics",
    "social media marketing", "email marketing", "excel", "powerpoint",
    "financial modeling", "market research",
    # Soft / general
    "communication", "leadership", "problem solving", "teamwork", "project management",
    "mentoring", "public speaking", "negotiation", "critical thinking",
    # Certifications / methodologies commonly listed as skills too
    "git", "github", "version control", "system design", "object oriented design",
    "distributed systems", "api design", "performance optimization",
})
