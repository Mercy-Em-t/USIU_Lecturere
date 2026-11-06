@echo off
title USIU-Africa Accessible Lecturer Grading Suite v2.0
echo ==========================================================================
echo   USIU-AFRICA ACCESSIBLE LECTURER ASSESSMENT ^& BLACKBOARD GRADER v2.0
echo ==========================================================================
echo.
echo [1/3] Running Multi-Format Rubric Grader (.txt, .docx, .pdf, .zip)...
python src\usiu_blackboard_grader.py --submissions-dir data\sample_submissions --out-csv data\outputs\USIU_Blackboard_GradeCenter_Upload.csv --out-json data\outputs\USIU_Grading_Audit_Report.json
echo.
echo [2/3] Opening Low-Vision High-Contrast Web Hub in Browser...
start "" "http://127.0.0.1:8085"
echo.
echo [3/3] Starting Local Python REST ^& SQLite 3NF Server on port 8085...
python src\usiu_lecturer_server.py --port 8085
pause
