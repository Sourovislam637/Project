#!/usr/bin/env python3
import re
import os
from bot import user_data, LOGGER, bot, DATABASE_URL
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.ext_utils.bot_utils import update_user_ldata
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands
from html import escape

def trun(text, limit=60):
    text = str(text)
    return text[:limit] + "..." if len(text) > limit else text

# Only these {tag} placeholders are supported in an Auto Rename format string.
VALID_AUTORENAME_TAGS = {'title', 'season', 'episode',
                          'quality', 'codec', 'audio', 'sub', 'size', 'language'}

# Telegram often trims a File Name (there's a length limit on it), so Season/
# Episode/Quality sometimes go missing from the actual filename even though
# they're still visible in the caption. These patterns are reused both for
# the filename itself and, as a fallback, for the caption text - the caption
# can come in very different shapes: a compact single line like
# "[RAH] The Exiled Heavy Knight Knows S01E04 [480p] Hindi.mkv", or a
# multi-line "Title - ...\nEpisode - 03\nSeason - 01\nQuality - 1080p\n..."
# style. The relaxed patterns below allow an optional space/colon/dash
# between the label and the number so both styles match, while a leading
# \b keeps a lone "S"/"E" from matching mid-word (e.g. it won't fire on
# "System" or misread "PS5" as Season 5).
SEASON_RE_STRICT = re.compile(r'(?:S|Season\s*)(\d{1,2})', re.IGNORECASE)
SEASON_RE_LOOSE = re.compile(r'\b(?:Season|S)[\s:.\-]{0,3}(\d{1,2})\b', re.IGNORECASE)
EPISODE_RE_STRICT = re.compile(r'(?:E|Ep|Episode\s*)(\d{1,3})', re.IGNORECASE)
EPISODE_RE_LOOSE = re.compile(r'\b(?:Episode|Ep|E)[\s:.\-]{0,3}(\d{1,3})\b', re.IGNORECASE)
# Handles a compact "S01E04" style token embedded anywhere in a caption -
# needs a \b before the S (so it won't fire on "PS5") and the E must follow
# right after the season digits (so it only matches an actual joint token).
SE_JOINT_RE = re.compile(r'\bS(\d{1,2})E(\d{1,3})\b', re.IGNORECASE)
QUALITY_RE = re.compile(r'(480p|540p|720p|1080p|1440p|2160p|4K)', re.IGNORECASE)
YEAR_RE = re.compile(r'\b(19\d{2}|20\d{2})\b')

# Very long captions (join-channel promos etc.) are capped before scanning,
# purely so a huge caption can't slow the regex pass down for no benefit -
# season/episode/quality info always lives near the top of a caption.
CAPTION_SCAN_LIMIT = 800


def validate_autorename_format(format_str):
    """
    Returns the set of {tag} placeholders used in an Auto Rename format
    string that aren't actually supported (e.g. a typo like {qualilty}).
    An unrecognized tag makes get_autorename() raise a KeyError and silently
    fall back to the original filename, which looks to the user like
    "Auto Rename isn't working" with no indication of why - so a format
    should be validated before it's ever saved.
    """
    used_tags = set(re.findall(r'\{([a-zA-Z_]+)\}', format_str))
    return used_tags - VALID_AUTORENAME_TAGS


def extract_season_episode_quality(name, caption=""):
    """
    Looks for Season / Episode / Quality first in `name` (typically the
    filename), then - only for whichever of those weren't found - in
    `caption` as a fallback. The caption fallback tries, in order: a compact
    joint "S01E04" style token (common when the filename itself was the
    caption's first line before Telegram trimmed the actual filename), then
    a "Season - 01" / "Episode: 03" key-value style line. Returns
    (season, episode, quality) as strings; season/episode are zero-padded to
    2 digits, quality is left as-is (e.g. "1080p"). Anything not found comes
    back as an empty string.
    """
    caption_text = caption[:CAPTION_SCAN_LIMIT] if caption else ""

    season_m = SEASON_RE_STRICT.search(name)
    season_val = season_m.group(1) if season_m else None
    episode_m = EPISODE_RE_STRICT.search(name)
    episode_val = episode_m.group(1) if episode_m else None

    if (season_val is None or episode_val is None) and caption_text:
        joint = SE_JOINT_RE.search(caption_text)
        if joint:
            if season_val is None:
                season_val = joint.group(1)
            if episode_val is None:
                episode_val = joint.group(2)
        if season_val is None:
            m = SEASON_RE_LOOSE.search(caption_text)
            season_val = m.group(1) if m else None
        if episode_val is None:
            m = EPISODE_RE_LOOSE.search(caption_text)
            episode_val = m.group(1) if m else None

    season = season_val.zfill(2) if season_val else ""
    episode = episode_val.zfill(2) if episode_val else ""

    quality_match = QUALITY_RE.search(name)
    if not quality_match and caption_text:
        quality_match = QUALITY_RE.search(caption_text)
    quality = quality_match.group(1) if quality_match else ""

    return season, episode, quality


def get_autorename(filename, user_id, size="", media_quality="", lang="", subs="", caption="", skip=False):
    """
    Advanced Auto Rename Logic: Cleans the filename and applies user format.
    Available Tags: {title}, {season}, {episode}, {quality}, {codec}, {audio}, {sub}, {size}, {language}

    - `caption`   : original Telegram caption of the file. Used as a fallback source to find
                    Season/Episode/Quality when the filename itself doesn't contain them
                    (Telegram's filename length limit can trim that info out).
    - `skip`      : if True, Auto Rename is bypassed completely and the original filename is
                    returned as-is. Used when the user has explicitly renamed the file via a
                    manual rename command/flag (e.g. "/l -n filename.mkv") so that command
                    should win over Auto Rename.
    """
    user_dict = user_data.get(user_id, {})

    # Manual rename (-n / -name) always wins over Auto Rename.
    if skip:
        return filename

    # Auto Rename disabled for this user -> return the original name untouched.
    if not user_dict.get('autorename', False):
        return filename

    # Default format set
    format_str = user_dict.get('autorename_format', '{title} - S{season}E{episode} - {quality} {codec} {audio} {sub}')
    if not format_str:
        format_str = '{title} - S{season}E{episode} - {quality}'

    name, ext = os.path.splitext(filename)

    # Did the user put a custom extension (.mkv, .mp4, etc.) at the very end
    # of their format string? If so, that extension is used; otherwise the
    # original file's extension is kept as-is.
    has_custom_ext = bool(re.search(r'\.[A-Za-z0-9]{2,5}$', format_str.strip()))

    season, episode, quality_from_text = extract_season_episode_quality(name, caption)
    quality = quality_from_text or media_quality

    codec_match = re.search(r'(x264|x265|HEVC|AV1|H264|H265|10bit|10Bit|AVC)', name, re.IGNORECASE)
    codec = codec_match.group(1) if codec_match else ""

    audio_match = re.search(r'(Dual[\s\-]?Audio|Multi[\s\-]?Audio|Hindi|English|Tamil|Telugu|Malayalam|Kannada|Bengali)', name, re.IGNORECASE)
    audio = audio_match.group(1).title() if audio_match else lang

    sub_match = re.search(r'(ESub|HC-ENG|MSub|Multi[\s\-]?Sub|Subbed)', name, re.IGNORECASE)
    sub = sub_match.group(1) if sub_match else subs

    # Clean the original name (strip bracketed/parenthesized tags and noise tokens).
    clean_title = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    noise_pattern = r'(S\d{1,2}|E\d{1,3}|Ep\s*\d{1,3}|Episode\s*\d{1,3}|480p|720p|1080p|1440p|2160p|4K|x264|x265|HEVC|AV1|H264|H265|10bit|10Bit|AVC|BluRay|WEB-DL|WEBRip|HDRip|HDTV|Dual[\s\-]?Audio|Multi[\s\-]?Audio|Hindi|English|Tamil|Telugu|Malayalam|Kannada|Bengali|ESub|HC-ENG|MSub|Multi[\s\-]?Sub|Subbed|Audio)'
    clean_title = re.sub(noise_pattern, '', clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r'(\s|-|\.)+', ' ', clean_title).strip()

    custom_title = user_dict.get('custom_title', '')
    final_title = custom_title if custom_title else clean_title

    try:
        new_name = format_str.format(
            title=final_title,
            season=season,
            episode=episode,
            quality=quality,
            codec=codec,
            audio=audio,
            sub=sub,
            size=size,
            language=audio
        )

        # Clean up a dangling "SE"/"S E" when Season and Episode are both missing,
        # and a dangling "E" (e.g. "S02E") when only Episode is missing.
        if not season and not episode:
            new_name = new_name.replace('SE', '').replace('S E', '')
        elif not season and episode:
            new_name = new_name.replace('SE', 'E')
        elif season and not episode:
            # Without this, a file where only the Season was found (e.g. from
            # "...S2..." with no episode number) would end up with a stray
            # "S02E" left in the name. Only the "E" directly after this
            # specific Season number is removed - not any other 'E' in the title.
            new_name = re.sub(rf'S{re.escape(season)}E(?!\d)', f'S{season}', new_name)

        # Clean up any extra spaces/dashes/dots left behind by the substitutions above.
        new_name = re.sub(r'\s+', ' ', new_name)
        new_name = re.sub(r'-\s*-', '-', new_name)
        new_name = re.sub(r'\.\s*\.', '.', new_name)
        new_name = new_name.strip(' -.')

        if not new_name:
            new_name = final_title

        # Extension handling: keep the user's custom extension if they set one,
        # otherwise fall back to the original file's extension.
        final_name = new_name if has_custom_ext else f"{new_name}{ext}"

        LOGGER.info(f"Auto Renamed: {filename} -> {final_name}")
        return final_name

    except KeyError as e:
        LOGGER.error(f"Auto Rename KeyError: Missing tag {e} in user format.")
        return filename
    except Exception as e:
        LOGGER.error(f"Auto Rename Error: {e}")
        return filename

# ==========================================
# /autorename Command Logic
# ==========================================

async def autorename_cmd(client, message):
    user_id = message.from_user.id

    if len(message.command) > 1:
        new_format = message.text.split(maxsplit=1)[1]
        if invalid_tags := validate_autorename_format(new_format):
            bad = ", ".join(f"{{{t}}}" for t in sorted(invalid_tags))
            await sendMessage(
                message,
                f"<b>⚠️ Invalid Tag(s) In Format:</b> <code>{escape(bad)}</code>\n\n"
                f"<b>Available Tags :</b> <code>{{title}}</code>, <code>{{season}}</code>, <code>{{episode}}</code>, "
                f"<code>{{quality}}</code>, <code>{{codec}}</code>, <code>{{audio}}</code>, <code>{{sub}}</code>, "
                f"<code>{{size}}</code>, <code>{{language}}</code>\n\n"
                f"<i>Format was not saved. Please fix the tag and try again.</i>"
            )
            return
        update_user_ldata(user_id, 'autorename_format', new_format)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
        await sendMessage(message, f"<b>Auto Rename Format Updated To:</b>\n<code>{escape(new_format)}</code>")
        return

    user_dict = user_data.get(user_id, {})
    buttons = ButtonMaker()

    auto_status = 'Enabled' if user_dict.get('autorename', False) else 'Disabled'
    format_str = user_dict.get('autorename_format', 'Not Exists')
    custom_title = user_dict.get('custom_title', 'Not Exists')

    text = f"㊂ <b><u>Auto Rename Settings :</u></b>\n\n"
    text += f"➲ <b>Status :</b> <i>{auto_status}</i>\n"
    text += f"➲ <b>Current Format :</b> <code>{escape(trun(format_str, 60))}</code>\n"
    text += f"➲ <b>Custom Title :</b> <code>{escape(trun(custom_title, 60))}</code>\n\n"
    text += f"➲ <b>Available Tags :</b> <code>{{title}}</code>, <code>{{season}}</code>, <code>{{episode}}</code>, <code>{{quality}}</code>, <code>{{codec}}</code>, <code>{{audio}}</code>, <code>{{sub}}</code>, <code>{{size}}</code>, <code>{{language}}</code>\n"
    text += f"➲ <b>Format Example :</b> <code>{{title}} S{{season}}E{{episode}} [{{quality}}] Hindi.mkv</code>\n\n"
    text += f"➲ <b>Description :</b> <i>Set your Custom Format and Title for Auto Renaming files. Custom Title will override {{title}}. Add an extension (.mkv/.mp4) at the end of the format to force it, otherwise the original file's extension is kept. Season/Episode/Quality are auto-detected from the filename, and from the file caption if missing in the name. A manual rename command (e.g. \"-n filename.mkv\") always overrides Auto Rename.</i>"

    buttons.ibutton("Disable" if auto_status == 'Enabled' else "Enable", f"userset {user_id} toggle_autorename")
    buttons.ibutton("Set Format", f"userset {user_id} autorename_format edit")
    buttons.ibutton("Set Custom Title", f"userset {user_id} custom_title edit")

    if format_str != 'Not Exists':
        buttons.ibutton("↻ Delete Format", f"userset {user_id} dautorename_format")
    if custom_title != 'Not Exists':
        buttons.ibutton("↻ Delete Title", f"userset {user_id} dcustom_title")

    buttons.ibutton("Close", f"userset {user_id} close", "footer")

    button = buttons.build_menu(2)
    await sendMessage(message, text, button)

# Command Handler
bot.add_handler(MessageHandler(autorename_cmd, filters=command(BotCommands.AutoRenameCommand) & CustomFilters.authorized_uset))
