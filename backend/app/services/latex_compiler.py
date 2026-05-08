import subprocess
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def compile_latex_file(tex_content: str, output_dir: str, filename: str = "main") -> Optional[str]:
    """
    Compiles LaTeX content to PDF using pdflatex.
    Returns the path to the generated PDF.
    """
    os.makedirs(output_dir, exist_ok=True)
    tex_path = os.path.join(output_dir, f"{filename}.tex")
    pdf_path = os.path.join(output_dir, f"{filename}.pdf")
    
    with open(tex_path, "w") as f:
        f.write(tex_content)
    
    try:
        # Run pdflatex twice (for references) with nonstopmode to push through errors
        for pass_num in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", f"{filename}.tex"],
                cwd=output_dir,
                check=False,
                capture_output=True,
                timeout=30,
                text=True
            )
            logger.info(f"pdflatex pass {pass_num + 1} returned code {result.returncode}")
        
        # Check if PDF was actually created regardless of return code
        if os.path.exists(pdf_path):
            return pdf_path
        else:
            logger.error(f"pdflatex did not produce a PDF file")
            logger.error(f"pdflatex stdout (last 500 chars): {result.stdout[-500:]}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("pdflatex timed out after 30 seconds")
        # Check if partial PDF exists
        if os.path.exists(pdf_path):
            return pdf_path
        return None
    except Exception as e:
        logger.error(f"pdflatex compilation error: {e}")
        return None

