@echo off
chcp 65001 >nul
echo ==========================================
echo CaptureMonitor 依赖安装脚本
echo ==========================================
echo.

echo [1/2] 安装 PaddleOCR...
pip install paddleocr paddlepaddle

echo.
echo [2/2] 安装翻译库（可选）...
echo 如果需要使用翻译功能，请运行：
echo    pip install googletrans-py

echo.
echo ==========================================
echo 安装完成！
echo ==========================================
echo.
echo 现在可以运行程序：
echo    python main.py
echo.
pause
