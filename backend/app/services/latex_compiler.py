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
    
    with open(tex_path, "w") as f:
        f.write(tex_content)
    
    try:
        # Run pdflatex with nonstopmode to prevent hanging on errors
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"{filename}.tex"],
            cwd=output_dir,
            check=False,
            capture_output=True,
            timeout=15,
            text=True
        )
        
        if result.returncode == 0:
            return os.path.join(output_dir, f"{filename}.pdf")
        else:
            logger.error(f"pdflatex failed with return code {result.returncode}")
            logger.error(f"pdflatex stdout: {result.stdout}")
            logger.error(f"pdflatex stderr: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("pdflatex timed out after 15 seconds")
        return None
    except Exception as e:
        logger.error(f"pdflatex compilation error: {e}")
        return None
