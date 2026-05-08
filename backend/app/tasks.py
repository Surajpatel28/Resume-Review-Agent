from app.core.celery_app import celery_app
from app.services.orchestrator import analyze_resume, generate_latex, edit_latex
from app.services.pdf_parser import pdf_parser
from app.services.latex_compiler import compile_latex_file
from app.core.db import SyncSessionLocal
from app.models.database import ResumeVersion, UserEdit
from sqlalchemy import select
import os


def _save_analysis_sync(version_id: int, analysis_json: dict, resume_text: str):
    """Save analysis results and extracted resume text to the DB."""
    with SyncSessionLocal() as session:
        result = session.execute(select(ResumeVersion).where(ResumeVersion.id == version_id))
        version = result.scalars().first()
        if version:
            version.analysis_json = analysis_json
            # Store resume text in tex_content temporarily so we can reuse it for fix
            version.tex_content = resume_text
            session.commit()


def _get_version_sync(version_id: int):
    """Get a version's tex_content (which holds resume_text before fix, or LaTeX after fix)."""
    with SyncSessionLocal() as session:
        result = session.execute(select(ResumeVersion).where(ResumeVersion.id == version_id))
        version = result.scalars().first()
        if version:
            return {
                "tex_content": version.tex_content or "",
                "analysis_json": version.analysis_json or {},
            }
        return {"tex_content": "", "analysis_json": {}}


def _save_fix_result_sync(version_id: int, tex_content: str, pdf_path: str):
    """Save the generated LaTeX and compiled PDF path."""
    with SyncSessionLocal() as session:
        result = session.execute(select(ResumeVersion).where(ResumeVersion.id == version_id))
        version = result.scalars().first()
        if version:
            version.tex_content = tex_content
            version.pdf_path = pdf_path
            session.commit()


def _save_edit_result_sync(project_id: int, version_id: int, instructions: str, result_tex: str, pdf_path: str):
    with SyncSessionLocal() as session:
        result = session.execute(
            select(ResumeVersion.version_number)
            .where(ResumeVersion.project_id == project_id)
            .order_by(ResumeVersion.version_number.desc())
        )
        last_version = result.scalars().first() or 0

        new_edit = UserEdit(
            version_id=version_id,
            instructions=instructions,
            result_tex=result_tex
        )
        session.add(new_edit)

        new_version = ResumeVersion(
            project_id=project_id,
            version_number=last_version + 1,
            tex_content=result_tex,
            pdf_path=pdf_path
        )
        session.add(new_version)
        session.commit()
        return new_version.id


# ─── STEP 1: Analyze Only (fast, ~2s) ───────────────────────────────────────

@celery_app.task(name="analyze_resume_task")
def analyze_resume_task(task_id: str, file_path: str, job_description: str, version_id: int, project_id: int):
    try:
        # 1. Extract text from PDF
        if os.path.exists(file_path):
            resume_text = pdf_parser.extract_text(file_path)
        else:
            resume_text = "No resume text found."

        # 2. Run ATS analysis
        analysis = analyze_resume(resume_text, job_description)
        analysis_json = analysis.model_dump() if analysis else {}

        # 3. Save analysis + resume_text to DB
        _save_analysis_sync(version_id, analysis_json, resume_text)

        return {
            "status": "completed",
            "task_id": task_id,
            "version_id": version_id,
            "project_id": project_id,
            "score": analysis.score if analysis else 0,
            "strengths": analysis.strengths if analysis else [],
            "weaknesses": analysis.weaknesses if analysis else [],
            "gap_report": analysis.gap_report if analysis else "",
        }

    except Exception as e:
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e)
        }


# ─── STEP 2: Fix Resume (LaTeX + PDF, on demand) ────────────────────────────

@celery_app.task(name="fix_resume_task")
def fix_resume_task(task_id: str, version_id: int, project_id: int, job_description: str):
    try:
        # 1. Get resume text saved during analysis
        version_data = _get_version_sync(version_id)
        resume_text = version_data["tex_content"]

        # 2. Generate optimized LaTeX
        tex_content = generate_latex(resume_text, job_description)

        # 3. Compile to PDF
        data_dir = "/app/data"
        if not os.path.exists(data_dir):
            data_dir = os.path.join(os.getcwd(), "data")
            os.makedirs(data_dir, exist_ok=True)

        pdf_path = compile_latex_file(tex_content, data_dir, filename=task_id)

        # 4. Save to DB
        _save_fix_result_sync(version_id, tex_content, pdf_path or "")

        return {
            "status": "completed",
            "task_id": task_id,
            "version_id": version_id,
            "project_id": project_id,
            "pdf_path": pdf_path,
        }

    except Exception as e:
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e)
        }


# ─── STEP 3: Iterative Edit ─────────────────────────────────────────────────

@celery_app.task(name="edit_resume_task")
def edit_resume_task(task_id: str, project_id: int, version_id: int, instructions: str):
    try:
        version_data = _get_version_sync(version_id)
        original_tex = version_data["tex_content"]

        new_tex = edit_latex(original_tex, instructions)

        data_dir = "/app/data"
        if not os.path.exists(data_dir):
            data_dir = os.path.join(os.getcwd(), "data")
            os.makedirs(data_dir, exist_ok=True)

        pdf_path = compile_latex_file(new_tex, data_dir, filename=task_id)

        new_version_id = _save_edit_result_sync(project_id, version_id, instructions, new_tex, pdf_path or "")

        return {
            "status": "completed",
            "task_id": task_id,
            "pdf_path": pdf_path,
            "project_id": project_id,
            "version_id": new_version_id,
        }
    except Exception as e:
        return {
            "status": "failed",
            "task_id": task_id,
            "error": str(e)
        }
