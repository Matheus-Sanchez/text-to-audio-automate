@echo off
cd /d %~dp0..
python -m app.cli.run --input data\entrada
pause
