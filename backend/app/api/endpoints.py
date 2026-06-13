from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.models.schemas import (
    ResumeUploadResponse,
    JobDescriptionRequest,
    AnalyzeResponse,
    FixResumeRequest,
    EditRequest,
    GenerateResponse,
    CompileRequest,
    CompileResponse,
)
from app.services.orchestrator import analyze_resume, generate_latex, edit_latex
from app.services.pdf_parser import pdf_parser
from app.services.latex_compiler import compile_latex_file
from uuid import uuid4
import os
import shutil

router = APIRouter()

DATA_DIR = "/app/data"
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.join(os.getcwd(), "data")
    os.makedirs(DATA_DIR, exist_ok=True)


# ─── Upload ──────────────────────────────────────────────────────────────────

@router.post("/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_id = uuid4()
    file_path = os.path.join(DATA_DIR, f"{file_id}.pdf")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return ResumeUploadResponse(id=file_id, filename=file.filename)


# ─── Step 1: Analyze (sync) ──────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(resume_id: str, jd: JobDescriptionRequest):
    file_path = os.path.join(DATA_DIR, f"{resume_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume file not found")

    resume_text = pdf_parser.extract_text(file_path)
    analysis = analyze_resume(resume_text, jd.text)

    return AnalyzeResponse(
        resume_id=resume_id,
        score=analysis.score,
        strengths=analysis.strengths,
        weaknesses=analysis.weaknesses,
        gap_report=analysis.gap_report,
    )


# ─── Step 2: Fix Resume (sync) ───────────────────────────────────────────────

@router.post("/fix-resume", response_model=GenerateResponse)
async def fix_resume(request: FixResumeRequest):
    file_path = os.path.join(DATA_DIR, f"{request.resume_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume file not found")

    resume_text = pdf_parser.extract_text(file_path)
    tex_content = generate_latex(resume_text, request.text)

    output_id = uuid4()
    pdf_path = compile_latex_file(tex_content, DATA_DIR, filename=str(output_id))
    if not pdf_path:
        raise HTTPException(status_code=500, detail="LaTeX compilation failed")

    return GenerateResponse(output_id=output_id, tex_content=tex_content)


# ─── Step 3: Iterative Edit (sync) ───────────────────────────────────────────

@router.post("/edit", response_model=GenerateResponse)
async def edit_resume(request: EditRequest):
    updated_tex = edit_latex(request.tex_content, request.instructions)

    output_id = uuid4()
    pdf_path = compile_latex_file(updated_tex, DATA_DIR, filename=str(output_id))
    if not pdf_path:
        raise HTTPException(status_code=500, detail="LaTeX compilation failed")

    return GenerateResponse(output_id=output_id, tex_content=updated_tex)


# ─── Standalone Compile ─────────────────────────────────────────────────────

@router.post("/compile", response_model=CompileResponse)
async def compile_latex_endpoint(request: CompileRequest):
    output_id = uuid4()
    pdf_path = compile_latex_file(request.tex_content, DATA_DIR, filename=str(output_id))
    if not pdf_path:
        raise HTTPException(status_code=500, detail="LaTeX compilation failed")

    return CompileResponse(output_id=output_id)


# ─── Downloads ───────────────────────────────────────────────────────────────

@router.get("/download/pdf/{output_id}")
async def download_pdf(output_id: str, download: bool = False):
    file_path = os.path.join(DATA_DIR, f"{output_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="resume_{output_id[:8]}.pdf"'
    else:
        headers["Content-Disposition"] = "inline"

    return FileResponse(file_path, media_type="application/pdf", headers=headers)


@router.get("/download/tex/{output_id}")
async def download_tex(output_id: str):
    file_path = os.path.join(DATA_DIR, f"{output_id}.tex")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="LaTeX source not found")
    return FileResponse(file_path, media_type="text/plain", headers={"Content-Disposition": "inline"})


# ─── Serve Predefined Template ───────────────────────────────────────────────

@router.get("/template")
async def get_template():
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "templates",
        "resume_template.tex",
    )
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Template not found")
    return FileResponse(template_path, media_type="text/plain")


# ─── Upload PDF → Editor (sync) ─────────────────────────────────────────────

@router.post("/resume-to-editor", response_model=GenerateResponse)
async def resume_to_editor(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_id = uuid4()
    file_path = os.path.join(DATA_DIR, f"{file_id}.pdf")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    resume_text = pdf_parser.extract_text(file_path)
    tex_content = generate_latex(resume_text, "")

    output_id = uuid4()
    pdf_path = compile_latex_file(tex_content, DATA_DIR, filename=str(output_id))
    if not pdf_path:
        raise HTTPException(status_code=500, detail="LaTeX compilation failed")

    return GenerateResponse(output_id=output_id, tex_content=tex_content)
