from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

# --- Resume Components Structured Schema ---

class PersonalInfo(BaseModel):
    name: str
    email: Optional[str] = None # Changed from EmailStr to str for resilience
    phone: Optional[str] = None
    location: Optional[str] = None
    links: List[str] = []

class Education(BaseModel):
    institution: str
    degree: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class Experience(BaseModel):
    company: str
    role: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    highlights: List[str] = []

class Project(BaseModel):
    title: str
    description: str
    links: List[str] = []
    technologies: List[str] = []

class ResumeSchema(BaseModel):
    personal_info: PersonalInfo
    summary: Optional[str] = None
    education: List[Education] = []
    experience: List[Experience] = []
    projects: List[Project] = []
    skills: List[str] = []

# --- API Request/Response Schemas ---

class ResumeUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str = "uploaded"

class JobDescriptionRequest(BaseModel):
    text: str

class AnalyzeRequest(BaseModel):
    resume_id: str
    job_description: str

class AnalysisResult(BaseModel):
    score: int
    strengths: List[str]
    weaknesses: List[str]
    gap_report: str

class JobDescriptionParsed(BaseModel):
    title: str
    company: Optional[str] = None
    required_skills: List[str]
    preferred_skills: List[str]
    experience_level: Optional[str] = None
    key_responsibilities: List[str]
    summary: str

class LatexOutput(BaseModel):
    latex_code: str

class ResumeVersion(BaseModel):
    id: int
    project_id: int
    version_number: int
    tex_content: str
    pdf_path: Optional[str] = None
    analysis_json: Optional[Dict[str, Any]] = None
    created_at: datetime

class CompileJob(BaseModel):
    tex_content: str

class UserEditRequest(BaseModel):
    project_id: int
    version_id: int
    instructions: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None

class ProcessTaskResult(BaseModel):
    status: str
    task_id: str
    pdf_path: Optional[str] = None
    version_id: int
    project_id: int
    score: int
    gap_report: str
    weaknesses: List[str]
