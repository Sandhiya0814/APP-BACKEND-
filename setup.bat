@echo off
set "VENV=c:\Users\sandh\Desktop\CDSS COPD\env"
cd "c:\Users\sandh\Desktop\CDSS COPD"
if not exist "CDSS_COPD" mkdir "CDSS_COPD"
cd "CDSS_COPD"
"%VENV%\Scripts\python.exe" -m django startproject backend .
"%VENV%\Scripts\python.exe" manage.py startapp api
