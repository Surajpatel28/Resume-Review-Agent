from pydantic import BaseModel
from typing import List
from uuid import UUID


class ResumeUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str = "uploaded"


class JobDescriptionRequest(BaseModel):
    text: str


class AnalysisResult(BaseModel):
    score: int
    strengths: List[str]
    weaknesses: List[str]
    gap_report: str


class AnalyzeResponse(BaseModel):
    resume_id: UUID
    score: int
    strengths: List[str]
    weaknesses: List[str]
    gap_report: str


class FixResumeRequest(BaseModel):
    resume_id: UUID
    text: str


class EditRequest(BaseModel):
    tex_content: str
    instructions: str


class GenerateResponse(BaseModel):
    output_id: UUID
    tex_content: str


class CompileRequest(BaseModel):
    tex_content: str


class CompileResponse(BaseModel):
    output_id: UUID
