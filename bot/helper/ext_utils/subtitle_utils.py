#!/usr/bin/env python3
"""
Intro Subtitle: adds a short softsub (a real, selectable subtitle track -
not burned into the video) that shows the user's own custom text for the
first few seconds of a leeched video, e.g. a channel/credit line.
"""

def validate_and_escape_subtitle_text(text):
    """
    Validate the user's raw subtitle text and reject anything that would
    break the generated SRT file. SRT itself only needs blank lines and the
    numeric/timestamp block left alone - it doesn't need FFmpeg drawtext-style
    character escaping (that only matters for burned-in/hardsub text, which
    Intro Subtitle doesn't use).

    Returns: (success: bool, result: str, error: str)
    """
    if not text or not text.strip():
        return False, "", "Subtitle text cannot be empty"

    text = text.strip()
    if len(text) > 200:
        return False, "", "Subtitle text too long (max 200 characters)"

    # Blank lines would break the single-block SRT structure generated below.
    text = text.replace("\r", "").replace("\n", " ")

    return True, text, ""


def create_subtitle_file(intro_settings, video_path):
    """
    Create a one-block SRT file showing the user's text for the configured
    duration, colored per their setting. Returns the SRT file's path, or
    None if no text is configured.
    """
    text = intro_settings.get("text", "")
    if not text:
        return None

    duration = intro_settings.get("duration", 5)
    color = intro_settings.get("color", "white")

    srt_content = (
        "1\n"
        f"00:00:00,000 --> 00:00:{duration:02d},000\n"
        f'<font color="{color}">{text}</font>\n'
    )

    srt_path = video_path.rsplit(".", 1)[0] + ".intro.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return srt_path


# Color options for the UI - standard SRT/mov_text <font color> names
COLOR_OPTIONS = {
    "white": "⚪ White",
    "black": "⚫ Black",
    "red": "🔴 Red",
    "blue": "🔵 Blue",
    "yellow": "🟡 Yellow",
    "green": "🟢 Green",
}
