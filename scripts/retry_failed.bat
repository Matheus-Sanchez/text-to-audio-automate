@echo off
cd /d %~dp0..
python -m app.cli.retry --failed
pause
