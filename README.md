# Week 2 Day 4 — Multi-PDF RAG App

## Requirements
- Python 3.10 or newer
- An OpenAI API key with API access/billing enabled
- Internet access for embedding and chat model calls

## Windows PowerShell setup

```powershell
cd "E:\AI SOCIAL EAGLE CLASS\WEEK -2"
mkdir "SE-AI-B12-1-W2D4 MultiPDF RAG App"
cd "SE-AI-B12-1-W2D4 MultiPDF RAG App"

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

$env:OPENAI_API_KEY="paste-your-api-key-here"
streamlit run rag_app.py
```

Keep the API key private. Do not put it in `rag_app.py`, README files, screenshots,
or GitHub. The environment variable above applies to the current PowerShell window.

If PowerShell blocks activation, you can avoid activation and run:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:OPENAI_API_KEY="paste-your-api-key-here"
.\.venv\Scripts\python.exe -m streamlit run rag_app.py
```

## Test checklist
1. Upload at least two text-based PDFs together.
2. Click **Build / rebuild document index**.
3. Confirm the indexed chunk count appears.
4. Ask a question answered by one PDF.
5. Ask a question that requires comparing two PDFs.
6. Confirm answers show source filenames and 1-based page numbers.
7. Test a question whose answer is absent; the app should say the PDFs do not provide enough information.
8. Take a screenshot of the answer and source list.

## GitHub
Create a new public or private repository, for example:
`Week-2-Day-4-MultiPDF-RAG-App`

Upload `rag_app.py`, `requirements.txt`, and `README.md`.
Do not upload `.venv/`, API keys, or private PDFs.
