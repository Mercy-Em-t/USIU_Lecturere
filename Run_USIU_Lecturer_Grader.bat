@echo off
title USIU-Africa Accessible Lecturer Grading & Blackboard Sync Suite
echo ====================================================================
echo   USIU-AFRICA ACCESSIBLE LECTURER ASSESSMENT ^& BLACKBOARD SUITE
echo ====================================================================
echo.
python "%~dp0src\usiu_blackboard_grader.py" --submissions-dir "%~dp0data\sample_submissions" --out-csv "%~dp0data\outputs\USIU_Blackboard_GradeCenter_Upload.csv" --out-json "%~dp0data\outputs\USIU_Grading_Audit_Report.json"
echo.
echo [DONE] Launching High-Contrast Low-Vision Lecturer Hub...
start "" "%~dp0index.html"
pause