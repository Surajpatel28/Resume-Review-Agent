import logging
from typing import Dict, Any, List, Optional
from app.models.schemas import AnalysisResult
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from app.core.config import settings
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize primary LLM based on settings
if settings.GROQ_API_KEY:
    logger.info("Using Groq API for inference")
    llm = ChatGroq(
        model_name="llama-3.1-8b-instant", 
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0,
        max_retries=2
    )
elif settings.USE_GEMINI and settings.GOOGLE_API_KEY:
    logger.info("Using Gemini API for inference (gemini-2.5-flash)")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
        timeout=300,
        max_retries=2
    )
else:
    from langchain_ollama import ChatOllama
    logger.info(f"Using Ollama ({settings.OLLAMA_MODEL}) for inference")
    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
    )

def analyze_resume(resume_text: str, jd_text: str) -> AnalysisResult:
    logger.info("Analyzing resume against JD")
    
    if not resume_text or not jd_text:
        return AnalysisResult(
            score=0, 
            strengths=[], 
            weaknesses=[], 
            gap_report="Missing resume or job description for analysis."
        )

    try:
        parser = PydanticOutputParser(pydantic_object=AnalysisResult)
        
        prompt = (
            "You are a hiring manager comparing a resume to a job description.\n\n"

            "Do three things:\n\n"

            "1. MATCHED SKILLS — Which JD requirements does the resume satisfy?\n"
            "   List ONLY the skill/tool names. No quotes, no evidence, just names.\n"
            "   Group related skills (e.g. 'Python, TensorFlow, OpenCV' as one entry if they appear together).\n"
            "   Maximum 6 entries.\n\n"

            "2. MISSING SKILLS — Which JD requirements are completely absent from the resume?\n"
            "   A skill is missing ONLY if the resume never mentions it at all.\n"
            "   If a skill appears in Matched Skills, it CANNOT appear here.\n"
            "   For each, write: 'SkillName — one sentence why it matters for this role'\n\n"

            "3. WEAK BULLETS — Pick 2 resume bullet points that are relevant but vaguely written.\n"
            "   For each, provide:\n"
            "   - The original bullet (exact quote)\n"
            "   - What is wrong (one sentence)\n"
            "   - A rewritten version\n\n"
            "   REWRITE RULES:\n"
            "   - Use ONLY facts from the resume (real company names, real tools, real projects)\n"
            "   - NEVER invent numbers, percentages, or metrics\n"
            "   - NEVER use brackets like [X]%, [Y], [dataset]\n"
            "   - Instead of fake metrics, describe the impact qualitatively\n"
            "     BAD: 'resulting in a 25% improvement in accuracy'\n"
            "     GOOD: 'improving classification accuracy across the production pipeline'\n\n"

            "OUTPUT:\n"
            "Return JSON:\n"
            "- 'score': 0\n"
            "- 'strengths': list of short strings (skill names or grouped names only)\n"
            "- 'weaknesses': list of strings ('Skill — reason')\n"
            "- 'gap_report': markdown string with sections ### Matched Skills, ### Missing Skills, ### Weak Bullets\n\n"

            "RULES:\n"
            "- Keep it concise. No walls of text.\n"
            "- No contradictions: if a skill is matched it cannot be missing.\n"
            "- No invented data. No placeholder brackets.\n"
            "- Output ONLY valid JSON. No markdown wrappers.\n"
            "- Escape newlines as \\n.\n\n"
            f"{parser.get_format_instructions()}\n\n"
            f"--- JOB DESCRIPTION ---\n{jd_text}\n\n"
            f"--- RESUME ---\n{resume_text}\n"
        )
        
        result = llm.invoke([HumanMessage(content=prompt)])
        content = result.content
        
        # Clean up any potential markdown formatting
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        return parser.parse(content)
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        return AnalysisResult(
            score=0,
            strengths=[],
            weaknesses=["Error analyzing resume"],
            gap_report=f"An error occurred during analysis: {str(e)}"
        )

def generate_latex(resume_text: str, jd_text: str) -> str:
    logger.info("Generating LaTeX code")
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "resume_template.tex")
    try:
        with open(template_path, "r") as f:
            template = f.read()
    except Exception as e:
        logger.error(f"Error reading template: {e}")
        template = "Please use a standard, professional LaTeX resume format."

    prompt = (
        "You are an expert LaTeX developer. Your task is to rewrite the provided resume to better match the job description, "
        "and output the final resume as completely valid, compilable LaTeX code.\n\n"
        "RULES:\n"
        "1. Return ONLY the raw LaTeX code.\n"
        "2. Do NOT wrap the code in ```latex blocks.\n"
        "3. Do NOT include any explanations or conversational text.\n"
        "4. Use the provided template as a structural guide.\n\n"
        f"--- TEMPLATE GUIDE ---\n{template}\n\n"
        f"--- JOB DESCRIPTION ---\n{jd_text}\n\n"
        f"--- ORIGINAL RESUME ---\n{resume_text}\n"
    )

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        
        # Clean up any potential markdown formatting
        if "```latex" in content:
            content = content.split("```latex")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        return content
    except Exception as e:
        logger.error(f"Error generating LaTeX: {e}")
        return "% Error generating LaTeX code."

def edit_latex(tex_content: str, edit_instructions: str) -> str:
    logger.info("Merging user edits into LaTeX")
    
    prompt = (
        "You are a LaTeX expert. Update the following LaTeX resume based EXACTLY on these instructions.\n\n"
        "RULES:\n"
        "1. Return ONLY the raw updated LaTeX code.\n"
        "2. Do NOT wrap the code in ```latex blocks.\n"
        "3. Do NOT include any explanations.\n\n"
        f"--- INSTRUCTIONS ---\n{edit_instructions}\n\n"
        f"--- CURRENT LATEX ---\n{tex_content}\n"
    )
    
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content
        
        # Clean up
        if "```latex" in content:
            content = content.split("```latex")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        return content
    except Exception as e:
        logger.error(f"Error merging user edits: {e}")
        return tex_content
