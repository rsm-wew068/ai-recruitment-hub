# AI Recruitment Hub 🌍

A modern, end-to-end AI-powered recruitment platform for job creation, candidate management, interview scheduling, analytics, and automated document generation.

---

## Project Structure

```
├── app.py                # Main Shiny app entrypoint
├── Dockerfile            # Container setup
├── pyproject.toml        # Python dependencies
├── data/                 # Source data (resumes, emails, context)
├── code/                 # Core logic (context, LLM connection)
├── server/               # Shiny server logic for each module (backend logic)
│   ├── candidate_profile.py      # Candidate profile backend logic
│   ├── correlation_analysis.py   # Correlation analysis backend logic
│   ├── document_creation.py      # Offer/contract PDF generation backend
│   ├── home.py                   # Home/dashboard backend logic
│   ├── interview_scheduler.py    # Interview scheduling backend logic
│   ├── job_creation.py           # Job creation backend logic
│   ├── plot_generation.py        # Analytics/chart backend logic
├── ui/                   # Shiny UI components for each module (frontend layout)
│   ├── candidate_profile.py      # Candidate profile UI
│   ├── chart_generation.py       # Analytics/chart UI
│   ├── correlation_analysis.py   # Correlation analysis UI
│   ├── document_creation.py      # Offer/contract UI
│   ├── home.py                   # Home/dashboard UI
│   ├── interview_scheduler.py    # Interview scheduling UI
│   ├── job_creation.py           # Job creation UI
├── static/, styles/      # Custom CSS
```

---

## End-to-End Workflow

1. **Job Creation:** Create job postings with details and requirements.
2. **Resume Upload:** Upload and parse candidate resumes, auto-link to jobs.
3. **Candidate Management:** Review, filter, and match candidates to jobs.
4. **Interview Scheduling:** Select candidates, generate LLM-powered interview emails, and send scheduling links (Calendly integration).
5. **Analytics:** Visualize candidate-job fit and correlations with interactive charts.
6. **Document Generation:** Auto-generate offer letters and contracts using LLMs, render as PDFs, and allow editing.
7. **Download & Edit:** Download, preview, and edit all generated documents.

---

## Full Pipeline

- **Data Ingestion:** Upload resumes (PDF), parse and extract candidate info.
- **Job Context:** Create and manage job postings, stored in `data/context.json`.
- **LLM Integration:** Use LLMs for drafting emails, offer letters, and contracts.
- **Scheduling:** Integrate with Calendly for interview scheduling links.
- **PDF Generation:** Render all communications and documents as PDFs, organized by job/candidate.
- **Analytics:** Generate charts and correlation plots for data-driven hiring.

---

## How to Use the App

1. **Navigate:**
   - Use the navbar to access Home, Job Creation, Candidate Profile, Interview Scheduler, Analytics, and Document Creation.
3. **Upload & Manage:**
   - Upload resumes, create jobs, and manage candidate profiles.
4. **Schedule Interviews:**
   - Select candidates, generate and send interview emails with scheduling links.
5. **Generate Documents:**
   - Create offer letters and contracts, preview and download as PDFs.
6. **Edit & Download:**
   - Edit generated documents and download the final versions.

---

## Technical Architecture

- **Frontend:** Shiny for Python (modular UI in `ui/`)
- **Backend:** Shiny server modules (`server/`), LLM integration, PDF generation
- **Data:** All context and files in `/data` and `/tmp/data` (mirrored for runtime)
- **LLM:** Uses Llama (via custom API) or Google Generative AI (Gemini) via `llm_connect.py`
- **Scheduling:** Calendly API integration
- **PDFs:** Generated with FPDF, stored per job/candidate
- **Containerization:** Docker for reproducible deployment

---

## Recently Implemented Improvements

- Robust PDF generation (handles encoding, layout, and font issues)
- Improved error handling for missing files and directories
- Modularized server and UI code for maintainability
- Enhanced document editing and download features
- Streamlined LLM prompt engineering for better document quality

---

## PDF Generation Notes

- FPDF is used for all PDF output. Font substitution warnings (e.g., Arial → Helvetica) are normal and do not affect PDF creation.
- Only Latin-1 characters are supported in PDFs due to FPDF limitations. Unsupported characters will be replaced automatically.

---

### 🤗 [Hugging Face Demo](https://github.com/rsm-wew068/graph-ai-task-manager.git)
