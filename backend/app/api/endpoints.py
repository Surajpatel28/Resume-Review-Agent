from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.schemas import (
    ResumeUploadResponse, JobDescriptionRequest, AnalysisResult,
    ResumeVersion as ResumeVersionSchema, UserEditRequest, TaskStatus
)
from app.models.database import Project, ResumeVersion, UserEdit
from app.core.db import get_db
from uuid import uuid4
from typing import List
import os
import shutil
from app.tasks import analyze_resume_task, fix_resume_task, edit_resume_task
from app.core.celery_app import celery_app

router = APIRouter()

DATA_DIR = "/app/data"
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.join(os.getcwd(), "data")
    os.makedirs(DATA_DIR, exist_ok=True)


# ─── Upload ──────────────────────────────────────────────────────────────────

@router.post("/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_id = uuid4()
    file_path = os.path.join(DATA_DIR, f"{file_id}.pdf")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return ResumeUploadResponse(id=file_id, filename=file.filename)


# ─── Step 1: Analyze Only ───────────────────────────────────────────────────

@router.post("/analyze")
async def analyze(
    resume_id: str,
    jd: JobDescriptionRequest,
    db: AsyncSession = Depends(get_db)
):
    file_path = os.path.join(DATA_DIR, f"{resume_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume file not found")

    # Create Project + Version in DB
    new_project = Project(name=f"Project {resume_id[:8]}")
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    new_version = ResumeVersion(project_id=new_project.id, tex_content="")
    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)

    task_id = str(uuid4())
    analyze_resume_task.apply_async(
        args=[task_id, file_path, jd.text, new_version.id, new_project.id],
        task_id=task_id
    )

    return {
        "status": "processing",
        "task_id": task_id,
        "project_id": new_project.id,
        "version_id": new_version.id
    }


# ─── Step 2: Fix Resume (on demand) ─────────────────────────────────────────

class FixResumeRequest(JobDescriptionRequest):
    project_id: int
    version_id: int

@router.post("/fix-resume")
async def fix_resume(request: FixResumeRequest):
    task_id = str(uuid4())
    fix_resume_task.apply_async(
        args=[task_id, request.version_id, request.project_id, request.text],
        task_id=task_id
    )
    return {"status": "processing", "task_id": task_id}


# ─── Step 3: Iterative Edit ─────────────────────────────────────────────────

@router.post("/edit")
async def edit_resume(request: UserEditRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResumeVersion).where(ResumeVersion.id == request.version_id))
    version = result.scalars().first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    task_id = str(uuid4())
    edit_resume_task.apply_async(
        args=[task_id, request.project_id, request.version_id, request.instructions],
        task_id=task_id
    )
    return {"status": "processing", "task_id": task_id}


# ─── Task Polling ────────────────────────────────────────────────────────────

@router.get("/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)
    result = None
    if task_result.ready():
        result = task_result.result
        if isinstance(result, Exception):
            result = {"error": str(result)}

    return TaskStatus(
        task_id=task_id,
        status=task_result.status,
        result=result
    )


# ─── Downloads ───────────────────────────────────────────────────────────────

@router.get("/download/pdf/{task_id}")
async def download_pdf(task_id: str, download: bool = False):
    file_path = os.path.join(DATA_DIR, f"{task_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="resume_{task_id[:8]}.pdf"'
    else:
        headers["Content-Disposition"] = "inline"
    
    return FileResponse(file_path, media_type='application/pdf', headers=headers)


@router.get("/download/tex/{task_id}")
async def download_tex(task_id: str):
    file_path = os.path.join(DATA_DIR, f"{task_id}.tex")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="LaTeX source not found")
    return FileResponse(file_path, media_type='text/plain', headers={"Content-Disposition": "inline"})
