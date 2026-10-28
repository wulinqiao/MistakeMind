param([int]$Port = 8000)
if (!(Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port $Port

