# 🧠 Resume Architect AI

An AI-powered resume optimization platform that analyzes resumes against job descriptions, identifies skill gaps, and generates ATS-compatible LaTeX resumes — all through a sleek, modern web interface.

<br/>

## ✨ Features

- **📊 Gap Analysis** — Upload your resume PDF + a job description to get an AI-driven skill gap report highlighting matched skills, missing requirements, and weak bullet points with suggested rewrites
- **📝 LaTeX Resume Generation** — Automatically converts your resume content into a clean, ATS-optimized LaTeX document using a professional template
- **✏️ Interactive LaTeX Editor** — Monaco-powered in-browser editor with live PDF preview, AI-assisted editing, and instant recompilation
- **🔄 Iterative AI Edits** — Natural language editing instructions (e.g. *"add Docker to skills"*) applied intelligently with a two-pass reasoning pipeline
- **📥 Multiple Entry Points** — Analyze → Fix flow, direct PDF-to-Editor upload, or start from a blank LaTeX template
- **🐳 Dockerized** — Single `docker compose up` to run the entire stack

<br/>

## 🏗️ Architecture

```
┌──────────────────────────────────┐
│          Frontend (Next.js)      │
│  React 19 · Tailwind · Monaco   │
│  Port 3000                       │
└───────────────┬──────────────────┘
                │  REST API
┌───────────────▼──────────────────┐
│          Backend (FastAPI)        │
│  LangChain · PyMuPDF · pdflatex  │
│  Port 8000                       │
├──────────────────────────────────┤
│  LLM Providers (priority order)  │
│  1. Groq (Llama 3.x)            │
│  2. Google Gemini                │
│  3. Ollama (local fallback)      │
│  + OpenRouter (reasoning edits)  │
└──────────────────────────────────┘
```

<br/>

## 🚀 Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- At least one LLM API key (Groq, Google Gemini, or a local Ollama instance)

### 1. Clone the Repository

```bash
git clone https://github.com/Surajpatel28/Resume-Review-Agent.git
cd Resume-Review-Agent
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required — at least one of:
GROQ_API_KEY=your_groq_key          # Recommended (fastest)
GOOGLE_API_KEY=your_google_key      # Alternative
USE_GEMINI=true                     # Set to true if using Gemini

# Optional
OPENROUTER_API_KEY=your_key         # Enables reasoning-enhanced edits
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

### 3. Launch

```bash
docker compose up --build
```

| Service   | URL                          |
| --------- | ---------------------------- |
| Frontend  | http://localhost:3000         |
| Backend   | http://localhost:8000         |
| API Docs  | http://localhost:8000/docs    |

<br/>

## 📖 Usage Workflows

### Flow 1: Analyze → Fix → Edit

1. Upload your resume PDF and paste the target job description
2. Click **Analyze Resume** to receive a gap analysis report
3. Review matched/missing skills and weak bullet rewrites
4. Click **Fix Resume** to generate an optimized LaTeX version
5. Fine-tune in the interactive editor with AI-powered edits
6. Download the final PDF or `.tex` source

### Flow 2: Direct PDF → Editor

1. Click **Upload PDF → Editor** on the homepage
2. Your resume is converted to LaTeX and opened in the editor immediately
3. Edit manually or use AI instructions to refine

### Flow 3: Blank Template

1. Click **Use Predefined Template** on the homepage
2. Start with a clean, professional LaTeX template
3. Fill in your details using the Monaco editor

<br/>

## 🔌 API Reference

All endpoints are prefixed with `/api`.

| Method | Endpoint              | Description                                      |
| ------ | --------------------- | ------------------------------------------------ |
| POST   | `/resume/upload`      | Upload a resume PDF, returns a `resume_id`       |
| POST   | `/analyze`            | Analyze resume against a job description         |
| POST   | `/fix-resume`         | Generate optimized LaTeX from resume + JD        |
| POST   | `/edit`               | Apply natural language edits to LaTeX source     |
| POST   | `/compile`            | Compile raw LaTeX to PDF                         |
| POST   | `/resume-to-editor`   | Upload PDF → extract text → generate LaTeX       |
| GET    | `/template`           | Fetch the predefined LaTeX template              |
| GET    | `/download/pdf/{id}`  | Download or preview a generated PDF              |
| GET    | `/download/tex/{id}`  | Download a generated LaTeX source file           |

<br/>

## 🗂️ Project Structure

```
Resume-Review-Agent/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI app + CORS config
│       ├── api/
│       │   └── endpoints.py        # REST API routes
│       ├── core/
│       │   └── config.py           # Pydantic settings (env vars)
│       ├── models/
│       │   └── schemas.py          # Request/response Pydantic models
│       ├── services/
│       │   ├── orchestrator.py     # LLM orchestration (analyze, generate, edit)
│       │   ├── pdf_parser.py       # PDF text extraction (PyMuPDF)
│       │   └── latex_compiler.py   # pdflatex compilation
│       └── templates/
│           └── resume_template.tex # Base LaTeX resume template
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── page.tsx            # Landing page (upload + JD input)
│       │   ├── analysis/page.tsx   # Gap analysis results view
│       │   ├── editor/page.tsx     # LaTeX editor + live PDF preview
│       │   ├── layout.tsx          # Root layout
│       │   └── globals.css         # Global styles + design tokens
│       ├── components/
│       │   ├── FileUpload.tsx      # File upload component
│       │   ├── GapReport.tsx       # Gap analysis display
│       │   ├── LatexEditor.tsx     # Monaco editor wrapper
│       │   └── ui/                 # shadcn/ui primitives
│       └── lib/
│           ├── api.ts              # Backend API client
│           └── utils.ts            # Utility functions
│
├── docker-compose.yml              # Multi-service orchestration
├── .env.example                    # Environment variable template
└── .gitignore
```

<br/>

## 🛠️ Tech Stack

| Layer        | Technology                                                              |
| ------------ | ----------------------------------------------------------------------- |
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Monaco Editor, shadcn/ui |
| **Backend**  | Python 3.11, FastAPI, Uvicorn, LangChain, Pydantic v2                  |
| **AI/LLM**   | Groq (Llama 3.1/3.3), Google Gemini 2.5 Flash, Ollama, OpenRouter      |
| **PDF**      | PyMuPDF (text extraction), pdfLaTeX (compilation), LaTeX               |
| **Infra**    | Docker, Docker Compose                                                  |

<br/>

## 🤖 LLM Provider Priority

The backend selects an LLM provider based on which API keys are configured:

1. **Groq** (if `GROQ_API_KEY` is set) — Llama 3.1 8B for analysis, Llama 3.3 70B for LaTeX generation
2. **Google Gemini** (if `USE_GEMINI=true` + `GOOGLE_API_KEY`) — Gemini 2.5 Flash for both tasks
3. **Ollama** (fallback) — Local model at `OLLAMA_BASE_URL`
4. **OpenRouter** (optional, `OPENROUTER_API_KEY`) — Used for reasoning-enhanced LaTeX editing with a two-pass reflection pipeline

<br/>

## 🧑‍💻 Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Requires pdflatex installed: sudo apt install texlive-latex-recommended texlive-latex-extra
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

> Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api` in `frontend/.env.local`

<br/>

## 📄 License

This project is open source — feel free to use, modify, and distribute.

<br/>

## 🙏 Acknowledgements

- [LangChain](https://www.langchain.com/) for LLM orchestration
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) for the in-browser code editing experience
- [shadcn/ui](https://ui.shadcn.com/) for beautiful UI components
- [Jake's Resume Template](https://www.overleaf.com/latex/templates/jakes-resume/syzfjbzwjncs) for LaTeX template inspiration
