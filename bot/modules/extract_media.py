#!/usr/bin/env python3
"""
/extract command.

Reply to a video (or a document/audio that contains multiple audio or
subtitle tracks) with /extract to pull out one or more Audio/Subtitle
tracks as their own files, with an interactive picker:
    1) Multi-select which tracks to extract (toggle on/off), then Done
    2) Output format - only asked when exactly one track is selected
       (Original/copy, or a re-encoded format); a multi-track batch is
       always extracted as Original/copy to keep things simple and fast.

Download and upload both show a live progress bar, same look as the
Leech DL/Up status. State between button taps is kept in bot_cache,
keyed by the command message id, and expires automatically after
EXTRACT_TIMEOUT seconds so a stale picker can't be reused against a
deleted temp file.
"""
from os import path as ospath
from time import time
from html import escape
from json import loads as jloads
from contextlib import suppress
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE

from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from langcodes import Language
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import bot, bot_cache, LOGGER
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.ext_utils.bot_utils import cmd_exec, new_task
from bot.helper.ext_utils.simple_progress import ProgressTracker

EXTRACT_WORKDIR = "Extracted"
EXTRACT_TIMEOUT = 300  # seconds a picker session stays valid before it expires

# key -> (Button Label, ffmpeg codec name or None for stream copy)
AUDIO_FORMATS = {
    'copy': ('Original', None),
    'aac':  ('AAC', 'aac'),
    'mp3':  ('MP3', 'libmp3lame'),
    'opus': ('OPUS', 'libopus'),
}
SUB_FORMATS = {
    'copy': ('Original', None),
    'srt':  ('SRT', 'srt'),
    'ass':  ('ASS', 'ass'),
}

AUDIO_EXT_MAP = {'aac': 'm4a', 'mp3': 'mp3', 'ac3': 'ac3', 'eac3': 'eac3', 'dts': 'dts',
                  'flac': 'flac', 'opus': 'opus', 'vorbis': 'ogg', 'truehd': 'thd', 'pcm_s16le': 'wav'}
SUB_EXT_MAP = {'subrip': 'srt', 'srt': 'srt', 'ass': 'ass', 'ssa': 'ssa', 'mov_text': 'srt', 'webvtt': 'vtt'}


def _guess_ext(codec_name, mtype):
    codec_name = (codec_name or '').lower()
    if mtype == 'audio':
        # mka (Matroska Audio) is a safe fallback container for any audio codec
        return AUDIO_EXT_MAP.get(codec_name, 'mka')
    # mks (Matroska Subtitle) safely wraps bitmap subs (PGS/VOBSUB) too
    return SUB_EXT_MAP.get(codec_name, 'mks')


async def _probe_streams(path):
    stdout, stderr, code = await cmd_exec(["ffprobe", "-hide_banner", "-loglevel", "error",
                                            "-print_format", "json", "-show_streams", path])
    if code != 0 or not stdout:
        LOGGER.error(f"Extract: ffprobe failed for {path} : {stderr}")
        return [], []
    try:
        streams = jloads(stdout).get('streams', [])
    except Exception as e:
        LOGGER.error(f"Extract: ffprobe json parse error: {e}")
        return [], []

    audios, subs = [], []
    a_idx = s_idx = 0
    for st in streams:
        ctype = st.get('codec_type')
        if ctype not in ('audio', 'subtitle'):
            continue
        lang = st.get('tags', {}).get('language', '')
        with suppress(Exception):
            lang = Language.get(lang).display_name() if lang else ''
        entry = {'lang': lang or 'Unknown', 'codec': (st.get('codec_name') or '').upper(),
                  'title': st.get('tags', {}).get('title', '')}
        if ctype == 'audio':
            entry['rel_idx'] = a_idx
            audios.append(entry)
            a_idx += 1
        else:
            entry['rel_idx'] = s_idx
            subs.append(entry)
            s_idx += 1
    return audios, subs


def _track_label(mtype, t, selected):
    mark = "✅" if (mtype, t['rel_idx']) in selected else "⬜"
    kind = "🎵" if mtype == 'audio' else "💬"
    label = f"{mark} {kind} {t['rel_idx'] + 1}. {t['lang']}"
    if t['title']:
        label += f" - {t['title'][:18]}"
    label += f" [{t['codec']}]"
    return label


def _select_menu(user_id, msg_id, cache):
    buttons = ButtonMaker()
    for t in cache['audios']:
        buttons.ibutton(_track_label('audio', t, cache['selected']), f"extract {user_id} {msg_id} toggle audio {t['rel_idx']}")
    for t in cache['subs']:
        buttons.ibutton(_track_label('sub', t, cache['selected']), f"extract {user_id} {msg_id} toggle sub {t['rel_idx']}")
    buttons.ibutton("✅ Done", f"extract {user_id} {msg_id} done", "footer")
    buttons.ibutton("Cancel", f"extract {user_id} {msg_id} cancel", "footer")
    count = len(cache['selected'])
    text = (f"<b>Select the Audio/Subtitle tracks to extract</b> (tap to toggle, {count} selected):\n"
            f"<i>Tap a track again to unselect it. Tap Done when ready.</i>")
    return text, buttons.build_menu(1)


@new_task
async def extract_media_cmd(client, message):
    rply = message.reply_to_message
    media = None
    if rply:
        media = next((m for m in [rply.video, rply.document, rply.audio] if m is not None), None)
    if not media:
        await sendMessage(
            message,
            f"<b>Reply to a Video/Audio/Document file with</b> <code>/{BotCommands.ExtractCommand[0]}</code>"
            f" <b>to extract Audio/Subtitle tracks from it.</b>"
        )
        return

    status = await sendMessage(message, "<i>Downloading...</i>")
    if not await aiopath.exists(EXTRACT_WORKDIR):
        await mkdir(EXTRACT_WORKDIR)

    file_name = media.file_name or f"{message.id}_media"
    local_path = ospath.join(EXTRACT_WORKDIR, f"{message.id}_{file_name}")
    tracker = ProgressTracker(status, "📥 Downloading", file_name)
    try:
        await rply.download(local_path, progress=tracker)
    except Exception as e:
        await editMessage(status, f"<b>Download Failed:</b> <code>{escape(str(e))}</code>")
        return

    await editMessage(status, "<i>Checking available Audio/Subtitle tracks...</i>")
    audios, subs = await _probe_streams(local_path)
    if not audios and not subs:
        await editMessage(status, "<b>No Audio or Subtitle tracks found in this file.</b>")
        with suppress(Exception):
            await aioremove(local_path)
        return

    bot_cache[message.id] = {'path': local_path, 'audios': audios, 'subs': subs,
                              'orig_name': file_name, 'selected': set(), 'time': time()}
    text, menu = _select_menu(message.from_user.id, message.id, bot_cache[message.id])
    await editMessage(status, text, menu)


@new_task
async def extract_callback(client, query):
    data = query.data.split()
    user_id, msg_id, stage = int(data[1]), int(data[2]), data[3]

    if query.from_user.id != user_id and not await CustomFilters.sudo(client, query):
        return await query.answer("This is not for you!", show_alert=True)

    cache = bot_cache.get(msg_id)
    if not cache:
        return await query.answer("Session expired, please send the command again.", show_alert=True)
    if time() - cache['time'] > EXTRACT_TIMEOUT:
        with suppress(Exception):
            await aioremove(cache['path'])
        del bot_cache[msg_id]
        return await editMessage(query.message, "<b>⏱ Timed Out. Please send the command again.</b>")
    cache['time'] = time()

    if stage == 'cancel':
        await query.answer()
        with suppress(Exception):
            await aioremove(cache['path'])
        del bot_cache[msg_id]
        return await editMessage(query.message, "<b>Cancelled.</b>")

    if stage == 'toggle':
        mtype, rel_idx = data[4], int(data[5])
        key = (mtype, rel_idx)
        if key in cache['selected']:
            cache['selected'].discard(key)
        else:
            cache['selected'].add(key)
        await query.answer()
        text, menu = _select_menu(user_id, msg_id, cache)
        return await editMessage(query.message, text, menu)

    if stage == 'done':
        if not cache['selected']:
            return await query.answer("Select at least one track first!", show_alert=True)
        await query.answer()
        if len(cache['selected']) == 1:
            mtype, rel_idx = next(iter(cache['selected']))
            fmt_map = AUDIO_FORMATS if mtype == 'audio' else SUB_FORMATS
            buttons = ButtonMaker()
            for key, (label, _) in fmt_map.items():
                buttons.ibutton(label, f"extract {user_id} {msg_id} go {mtype} {rel_idx} {key}")
            buttons.ibutton("« Back", f"extract {user_id} {msg_id} back", "footer")
            buttons.ibutton("Cancel", f"extract {user_id} {msg_id} cancel", "footer")
            return await editMessage(query.message, "<b>Select output format:</b>", buttons.build_menu(2))
        # Multiple tracks selected - extract all of them as Original/copy.
        return await _do_extract_batch(client, query, cache)

    if stage == 'back':
        text, menu = _select_menu(user_id, msg_id, cache)
        await query.answer()
        return await editMessage(query.message, text, menu)

    if stage == 'go':
        mtype, rel_idx, fmt_key = data[4], int(data[5]), data[6]
        await query.answer()
        return await _do_extract_one(client, query, cache, mtype, rel_idx, fmt_key)


async def _extract_one_file(cache, mtype, rel_idx, fmt_key):
    """Runs ffmpeg for a single track and returns (ok, out_path_or_err, track, label)."""
    tracks = cache['audios'] if mtype == 'audio' else cache['subs']
    track = next((t for t in tracks if t['rel_idx'] == rel_idx), None)
    if not track:
        return False, "Track not found, session may be stale.", None, None

    fmt_map = AUDIO_FORMATS if mtype == 'audio' else SUB_FORMATS
    label, codec = fmt_map[fmt_key]
    ext = _guess_ext(track['codec'], mtype) if fmt_key == 'copy' else fmt_key
    src_base = ospath.splitext(cache['orig_name'])[0]
    out_path = ospath.join(EXTRACT_WORKDIR, f"{src_base}_{mtype}_{rel_idx + 1}.{ext}")

    stream_selector = f"0:{'a' if mtype == 'audio' else 's'}:{rel_idx}"
    cmd = [bot_cache['pkgs'][2], "-hide_banner", "-loglevel", "error", "-i", cache['path'], "-map", stream_selector]
    cmd += ["-c", "copy"] if codec is None else [f'-c:{"a" if mtype == "audio" else "s"}', codec]
    cmd.append(out_path)

    proc = await create_subprocess_exec(*cmd, stderr=PIPE)
    code = await proc.wait()
    if code != 0 or not await aiopath.exists(out_path):
        err = (await proc.stderr.read()).decode().strip()
        LOGGER.error(f"Extract failed: {err}")
        return False, err, track, label
    return True, out_path, track, label


async def _upload_extracted(client, query, out_path, mtype, track, label, orig_name):
    kind = 'Audio' if mtype == 'audio' else 'Subtitle'
    caption = (f"<b>{track['lang']} {label} {kind}</b>\n"
               f"<b>Extracted From:</b> <code>{escape(orig_name)}</code>")
    up_status = await query.message.reply(f"<i>Uploading {escape(ospath.basename(out_path))}...</i>")
    tracker = ProgressTracker(up_status, "📤 Uploading", ospath.basename(out_path))
    try:
        if mtype == 'audio':
            await client.send_audio(chat_id=query.message.chat.id, audio=out_path, caption=caption, progress=tracker)
        else:
            await client.send_document(chat_id=query.message.chat.id, document=out_path, caption=caption, progress=tracker)
        await editMessage(up_status, f"<b>✅ Uploaded:</b> <code>{escape(ospath.basename(out_path))}</code>")
        return True
    except Exception as e:
        LOGGER.error(f"Extract upload failed: {e}")
        await editMessage(up_status, f"<b>Upload Failed:</b> <code>{escape(str(e))}</code>")
        return False
    finally:
        with suppress(Exception):
            await aioremove(out_path)


async def _do_extract_one(client, query, cache, mtype, rel_idx, fmt_key):
    msg_id = int(query.data.split()[2])
    await editMessage(query.message, "<i>Extracting, please wait...</i>")
    ok, result, track, label = await _extract_one_file(cache, mtype, rel_idx, fmt_key)
    if not ok:
        return await editMessage(query.message, f"<b>Extraction Failed:</b>\n<code>{escape(str(result)[:300])}</code>")
    await editMessage(query.message, "<b>Extraction Complete, Uploading...</b>")
    await _upload_extracted(client, query, result, mtype, track, label, cache['orig_name'])
    with suppress(Exception):
        await aioremove(cache['path'])
    bot_cache.pop(msg_id, None)


async def _do_extract_batch(client, query, cache):
    msg_id = int(query.data.split()[2])
    total = len(cache['selected'])
    done_count = 0
    for mtype, rel_idx in list(cache['selected']):
        done_count += 1
        await editMessage(query.message, f"<i>Extracting {done_count}/{total}...</i>")
        ok, result, track, _label_key = await _extract_one_file(cache, mtype, rel_idx, 'copy')
        label = (AUDIO_FORMATS if mtype == 'audio' else SUB_FORMATS)['copy'][0]
        if not ok:
            await query.message.reply(f"<b>⚠️ Failed to extract track {rel_idx + 1} ({mtype}):</b>\n<code>{escape(str(result)[:200])}</code>")
            continue
        await _upload_extracted(client, query, result, mtype, track, label, cache['orig_name'])

    await editMessage(query.message, f"<b>✅ Done. Extracted {total} track(s).</b>")
    with suppress(Exception):
        await aioremove(cache['path'])
    bot_cache.pop(msg_id, None)


bot.add_handler(MessageHandler(extract_media_cmd, filters=command(BotCommands.ExtractCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(extract_callback, filters=regex("^extract")))
