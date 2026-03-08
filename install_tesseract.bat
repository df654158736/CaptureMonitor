@echo off
chcp 65001 >nul
echo ==========================================
echo Tesseract OCR 安装助手
echo ==========================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [错误] 请以管理员身份运行此脚本！
    echo 右键点击脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

echo [1/4] 正在安装 pytesseract...
pip install pytesseract pillow

echo.
echo [2/4] 正在下载 Tesseract OCR...
echo 下载地址: https://github.com/UB-Mannheim/tesseract/wiki

:: Check if Tesseract is already installed
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo.
    echo [信息] Tesseract 已安装在 C:\Program Files\Tesseract-OCR\
    goto :configure
)

if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    echo.
    echo [信息] Tesseract 已安装在 C:\Program Files (x86)\Tesseract-OCR\
    goto :configure
)

echo.
echo 请手动下载并安装 Tesseract OCR：
echo.
echo 1. 打开浏览器访问：
echo    https://github.com/UB-Mannheim/tesseract/wiki
echo.
echo 2. 下载最新版本的 tesseract-ocr-w64-setup.exe
echo.
echo 3. 运行安装程序，记住安装路径（默认：C:\Program Files\Tesseract-OCR）
echo.
echo 4. 安装完成后，重新运行此脚本
echo.
start https://github.com/UB-Mannheim/tesseract/wiki
pause
exit /b

:configure
echo.
echo [3/4] 正在配置环境变量...
setx /M PATH "%PATH%;C:\Program Files\Tesseract-OCR;C:\Program Files\Tesseract-OCR\bin" 2>nul
if %errorLevel% neq 0 (
    echo [警告] 无法自动添加环境变量，请手动添加以下路径到 PATH：
    echo    C:\Program Files\Tesseract-OCR
    echo    C:\Program Files\Tesseract-OCR\bin
)

echo.
echo [4/4] 下载中文语言包...
if not exist "C:\Program Files\Tesseract-OCR\tessdata\chi_sim.traineddata" (
    echo 正在下载中文语言包...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata' -OutFile 'C:\Program Files\Tesseract-OCR\tessdata\chi_sim.traineddata'"
    if %errorLevel% neq 0 (
        echo [警告] 无法自动下载中文语言包
        echo 请手动下载：
        echo https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata
        echo 并放到：C:\Program Files\Tesseract-OCR\tessdata\
    )
) else (
    echo 中文语言包已存在
)

echo.
echo ==========================================
echo 安装完成！
echo ==========================================
echo.
echo 请重新打开命令行窗口，然后运行：
echo    python main.py
echo.
pause
