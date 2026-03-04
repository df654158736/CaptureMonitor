"""
Screen capture utility for capturing regions of the screen.
"""

from PIL import Image
import pyautogui


def capture_region(x: int, y: int, width: int, height: int) -> Image.Image:
    """
    Capture a region of the screen.

    Args:
        x: X coordinate of the top-left corner
        y: Y coordinate of the top-left corner
        width: Width of the region
        height: Height of the region

    Returns:
        PIL Image of the captured region
    """
    if width <= 0 or height <= 0:
        return Image.new('RGB', (1, 1), color='white')

    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    return screenshot
