#!/usr/bin/env python3
"""
A small, self-contained Download/Upload progress bar for standalone tools
(Extract, Merge) that don't run through the main Task engine and so don't
show up on the /status page - this gives the same look and feel
(progress bar, percentage, processed/total size, speed, ETA) as the main
Leech DL/Up status, just by periodically editing its own status message.
"""
from time import time

from bot.helper.ext_utils.bot_utils import get_progress_bar_string, get_readable_file_size, get_readable_time
from bot.helper.telegram_helper.message_utils import editMessage

EDIT_THROTTLE = 4  # minimum seconds between status message edits (stays clear of flood limits)


class ProgressTracker:
    """
    Usage: pass an instance directly as pyrogram's `progress=` callback to
    message.download(...) or client.send_video/send_audio/send_document(...).
    Pyrogram calls it as progress(current, total).
    """

    def __init__(self, status_msg, label, filename=""):
        self.status_msg = status_msg
        self.label = label
        self.filename = filename
        self.last_edit = 0.0
        self.last_bytes = 0
        self.last_time = time()

    async def __call__(self, current, total):
        now = time()
        done = total and current >= total
        if not done and now - self.last_edit < EDIT_THROTTLE:
            return

        elapsed = now - self.last_time
        speed = (current - self.last_bytes) / elapsed if elapsed > 0 else 0
        self.last_bytes, self.last_time = current, now

        pct = (current / total * 100) if total else 0
        eta = (total - current) / speed if speed > 0 else 0

        text = (
            f"<b>{self.label}</b>" + (f" : <code>{self.filename}</code>" if self.filename else "") + "\n\n"
            f"{get_progress_bar_string(pct)} {round(pct, 1)}%\n"
            f"<b>Processed :</b> {get_readable_file_size(current)} of {get_readable_file_size(total)}\n"
            f"<b>Speed :</b> {get_readable_file_size(speed)}/s | <b>ETA :</b> {get_readable_time(eta) if speed > 0 else '-'}"
        )
        self.last_edit = now
        try:
            await editMessage(self.status_msg, text)
        except Exception:
            pass
