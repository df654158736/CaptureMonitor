@echo off
chcp 65001 >nul
echo ==========================================
echo CaptureMonitor 依赖安装脚本
echo ==========================================
echo.

echo [1/3] 安装 Tesseract OCR...
pip install pytesseract pillow

echo.
echo [2/3] 安装翻译库...
pip install googletrans-py

echo.
echo [3/3] 安装 PaddleOCR（可选）...
echo 如果您需要使用 PaddleOCR，请运行：
echo    pip install paddleocr

echo.
echo ==========================================
echo 安装完成！
echo ==========================================
echo.
echo 现在可以运行程序：
echo    python main.py
echo.
pause
