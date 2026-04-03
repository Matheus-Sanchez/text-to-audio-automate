@echo off
cd /d %~dp0..
py -3.11 -m app.cli.status --last 20
pause
