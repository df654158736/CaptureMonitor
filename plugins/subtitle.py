"""
Subtitle Monitor Plugin

A plugin for monitoring video subtitles and other text content.
Processes text by merging lines and removing extra whitespace.
"""


def plugin_info() -> dict:
    """
    Return plugin metadata.

    Returns:
        Dictionary with plugin information
    """
    return {
        "name": "Subtitle Monitor",
        "description": "For monitoring video subtitles and general text",
        "version": "1.0.0",
        "author": "CaptureMonitor"
    }


def process_text(text: str) -> str:
    """
    Process raw OCR text for subtitle monitoring.

    Merges multiple lines into a single line and removes
    extra whitespace.

    Args:
        text: Raw OCR text

    Returns:
        Processed text
    """
    if not text:
        return ""

    # Replace newlines with spaces
    text = text.replace('\n', ' ').replace('\r', ' ')

    # Remove extra whitespace
    text = ' '.join(text.split())

    return text.strip()


def format_change(old: str, new: str) -> str:
    """
    Format a change for display.

    Args:
        old: Previous text
        new: Current text

    Returns:
        Formatted change string
    """
    return f"{old} \u2192 {new}"
