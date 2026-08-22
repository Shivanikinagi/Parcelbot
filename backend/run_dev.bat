@echo off
cd /d "%~dp0"
"C:\Users\ShivaniKinagi\OneDrive - Trinamix Systems Pvt Ltd\Desktop\project\parcelbot\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000
