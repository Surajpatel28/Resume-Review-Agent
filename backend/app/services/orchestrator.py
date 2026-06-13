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
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

openrouter_client = None
if settings.OPENROUTER_API_KEY and OpenAI:
    logger.info("Using OpenRouter API with reasoning capabilities")
    openrouter_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
    )

# Fast LLM for analysis (small, quick)
if settings.GROQ_API_KEY:
    logger.info("Using Groq API for inference")
    llm = ChatGroq(
        model_name="llama-3.1-8b-instant", 
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0,
        max_retries=2
    )
    # Strong LLM for LaTeX generation (larger model, better at structured output)
    llm_latex = ChatGroq(
        model_name="llama-3.3-70b-versatile",
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
    llm_latex = llm  # Gemini is already strong enough
else:
    from langchain_ollama import ChatOllama
    logger.info(f"Using Ollama ({settings.OLLAMA_MODEL}) for inference")
    llm = ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
    )
    llm_latex = llm

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
            "Return JSON exactly matching this schema:\n"
            "- 'score': 0\n"
            "- 'strengths': [list of short skill names from step 1]\n"
            "- 'weaknesses': [list of missing skills from step 2, formatted exactly as 'Skill — reason']\n"
            "- 'gap_report': markdown string with sections ### Matched Skills, ### Missing Skills, ### Weak Bullets (from step 3)\n\n"

            "CRITICAL RULES:\n"
            "- Do NOT put weak bullets in the 'weaknesses' array. The 'weaknesses' array is ONLY for missing skills (e.g. 'Docker — Required for deployment').\n"
            "- Keep 'strengths' very short (1-3 words per item).\n"
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

def _ensure_latex_complete(tex: str) -> str:
    """Ensure LaTeX document is structurally complete."""
    tex = tex.strip()
    # Count open/close environments
    opens = tex.count('\\begin{itemize}') + tex.count('\\resumeItemListStart') + tex.count('\\resumeSubHeadingListStart')
    closes = tex.count('\\end{itemize}') + tex.count('\\resumeItemListEnd') + tex.count('\\resumeSubHeadingListEnd')
    # Add missing closings
    for _ in range(opens - closes):
        tex += '\n\\end{itemize}'
    if '\\begin{document}' in tex and '\\end{document}' not in tex:
        tex += '\n\\end{document}'
    return tex

def _clean_latex_response(content: str) -> str:
    """Strip markdown wrappers from LLM response."""
    if "```latex" in content:
        content = content.split("```latex")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return content

def generate_latex(resume_text: str, jd_text: str) -> str:
    logger.info("Generating LaTeX code")
    
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "resume_template.tex")
    try:
        with open(template_path, "r") as f:
            template = f.read()
    except Exception as e:
        logger.error(f"Error reading template: {e}")
        template = ""

    prompt = (
        "You are a LaTeX resume generator. Output ONLY raw LaTeX code, no markdown wrappers.\n\n"

        "CONTENT:\n"
        "- Preserve all contact info (name, email, phone, URLs) character-for-character from the resume.\n"
        "- Preserve all projects, experiences, education, and achievements exactly. Do NOT invent any.\n"
        "- MUST add JD-relevant skills to Technical Skills (e.g. if JD needs Spring Boot, MySQL, Redis — add them).\n"
        "- May rephrase bullet wording for impact, but keep all facts unchanged.\n"
        "- Omit sections with zero entries (e.g. empty Experience).\n\n"

        "FORMAT:\n"
        "- Header: \\href{actual-url}{\\underline{Label}} with $|$ separators. Use real URLs from resume data.\n"
        "- Skills: split into Languages / ML-NLP / Frameworks / Tools sub-groups.\n"
        "- Capitalization: TensorFlow, PyTorch, NumPy, Scikit-Learn, Data Structures and Algorithms.\n"
        "- Projects: title in \\resumeProjectHeading, tech stack on next line via \\resumeProjectTech.\n"
        "- \\resumeSubheading takes exactly 4 args: {Title}{Location}{Subtitle}{Dates}.\n"
        "- One page max. Start with \\documentclass, end with \\end{document}. Balance all environments.\n\n"

        f"--- TEMPLATE ---\n{template}\n\n"
        f"--- JD ---\n{jd_text[:2000]}\n\n"
        f"--- RESUME ---\n{resume_text[:4000]}\n"
    )

    try:
        response = llm_latex.invoke([HumanMessage(content=prompt)])
        content = _clean_latex_response(response.content)
        content = _ensure_latex_complete(content)
        return content
    except Exception as e:
        logger.error(f"Error generating LaTeX: {e}")
        return "% Error generating LaTeX code."

def edit_latex(tex_content: str, edit_instructions: str) -> str:
    logger.info("Merging user edits into LaTeX")
    
    prompt = (
        "Apply the edits below to this LaTeX resume. Output ONLY the complete updated LaTeX code.\n\n"
        "RULES:\n"
        "- Do NOT change contact info, projects, or experiences unless explicitly asked.\n"
        "- Technical Skills section is freely editable.\n"
        "- Omit empty sections. Use \\href{url}{\\underline{Label}} for links.\n"
        "- Correct caps: TensorFlow, PyTorch, NumPy, Data Structures and Algorithms.\n"
        "- \\resumeSubheading takes 4 args. Balance all \\begin/\\end. No markdown wrappers.\n"
        "- Return the FULL document from \\documentclass to \\end{document}.\n\n"
        f"--- EDITS ---\n{edit_instructions}\n\n"
        f"--- CURRENT LATEX ---\n{tex_content}\n"
    )
    
    try:
        if not openrouter_client:
            logger.info("OpenRouter not configured; using default LLM for edit_latex.")
            response = llm_latex.invoke([HumanMessage(content=prompt)])
            content = _clean_latex_response(response.content)
            content = _ensure_latex_complete(content)
            return content

        logger.info("Calling OpenRouter with reasoning enabled for edit_latex (Step 1)")
        response = openrouter_client.chat.completions.create(
            model="moonshotai/kimi-k2.6",
            messages=[
                {"role": "user", "content": prompt}
            ],
            extra_body={"reasoning": {"enabled": True}}
        )
        assistant_message = response.choices[0].message

        messages = [
            {"role": "user", "content": prompt},
            {
                "role": "assistant",
                "content": assistant_message.content,
            },
            {"role": "user", "content": "Are you sure? Think carefully."}
        ]

        if hasattr(assistant_message, 'reasoning_details'):
            messages[1]["reasoning_details"] = assistant_message.reasoning_details

        logger.info("Calling OpenRouter with reasoning enabled for edit_latex (Step 2 - Reflection)")
        response2 = openrouter_client.chat.completions.create(
            model="moonshotai/kimi-k2.6",
            messages=messages,
            extra_body={"reasoning": {"enabled": True}}
        )
        content = response2.choices[0].message.content

        content = _clean_latex_response(content)
        content = _ensure_latex_complete(content)
        return content
    except Exception as e:
        logger.error(f"Error merging user edits: {e}")
        return tex_content
