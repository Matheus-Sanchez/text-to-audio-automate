@echo off
cd /d %~dp0..
py -3.11 -m app.cli.run
pause
