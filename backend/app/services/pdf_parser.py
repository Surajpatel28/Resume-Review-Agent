import fitz # PyMuPDF

class PDFParser:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text from a PDF file using PyMuPDF."""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            # In a real app, use proper logging
            print(f"Error parsing PDF: {e}")
            return ""

pdf_parser = PDFParser()
