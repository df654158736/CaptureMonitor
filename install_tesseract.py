#!/usr/bin/env python3
"""
Tesseract OCR 安装检查脚本
运行: python install_tesseract.py
"""

import subprocess
import sys
import os
import platform

def install_pytesseract():
    """安装 pytesseract Python 包"""
    print("[1/3] 正在安装 pytesseract...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytesseract", "-q"])
    print("✓ pytesseract 安装完成")

def check_tesseract():
    """检查 Tesseract 是否已安装"""
    print("[2/3] 检查 Tesseract OCR 引擎...")

    common_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]

    for path in common_paths:
        if os.path.exists(path):
            print(f"✓ 找到 Tesseract: {path}")
            return True

    print("✗ 未找到 Tesseract OCR 引擎")
    return False

def print_install_instructions():
    """打印安装说明"""
    print("""
[3/3] 请手动安装 Tesseract OCR:

方法 1 - 自动安装（推荐）:
1. 下载安装程序:
   https://github.com/UB-Mannheim/tesseract/wiki

2. 运行安装程序，选择默认路径:
   C:\\Program Files\\Tesseract-OCR

3. 确保勾选 "Add to PATH" 选项

方法 2 - 使用 Chocolatey:
   choco install tesseract

方法 3 - 使用 Scoop:
   scoop install tesseract

安装完成后，重新运行此脚本或 main.py
""")

def main():
    print("=" * 50)
    print("Tesseract OCR 安装检查")
    print("=" * 50)
    print()

    # 安装 pytesseract
    try:
        install_pytesseract()
    except Exception as e:
        print(f"✗ 安装失败: {e}")
        return

    # 检查 Tesseract
    if check_tesseract():
        print()
        print("=" * 50)
        print("✓ 所有组件已就绪！")
        print("=" * 50)
        print()
        print("现在可以运行: python main.py")
    else:
        print_install_instructions()
        # 自动打开下载页面
        import webbrowser
        webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki")

if __name__ == "__main__":
    main()
