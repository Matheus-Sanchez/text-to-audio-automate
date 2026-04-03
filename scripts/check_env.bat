@echo off
cd /d %~dp0..
py -3.11 check_setup.py
pause
