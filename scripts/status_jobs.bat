@echo off
cd /d %~dp0..
python -m app.cli.status --last 20
pause
