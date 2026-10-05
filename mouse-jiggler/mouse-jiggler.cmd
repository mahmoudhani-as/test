@echo off
rem Double-click to start. Close the window (or press Ctrl+C) to stop.
rem Optional: mouse-jiggler.cmd -Pixels 10 -IntervalSeconds 30
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0mouse-jiggler.ps1" %*
