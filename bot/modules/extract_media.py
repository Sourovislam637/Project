#!/usr/bin/env python3
"""
/extract command.

Reply to a video (or a document/audio that contains multiple audio or
subtitle tracks) with /extract to pull out one specific Audio or Subtitle
track as its own file, with an interactive picker for:
    1) Track type (Audio / Subtitle) - skipped if only one type exists
    2) Which track (by detected language + codec)
    3) Output format (Original/copy, or a re-encoded format)

State between button taps is kept in bot_cache, keyed by the command
message id, and expires automatically after EXTRACT_TIMEOUT seconds so a
stale picker can't be reused against a deleted temp file.
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


def _type_menu(user_id, msg_id, audios, subs):
    buttons = ButtonMaker()
    if audios:
        buttons.ibutton(f"🎵 Audio ({len(audios)})", f"extract {user_id} {msg_id} type audio")
    if subs:
        buttons.ibutton(f"💬 Subtitle ({len(subs)})", f"extract {user_id} {msg_id} type sub")
    buttons.ibutton("Cancel", f"extract {user_id} {msg_id} cancel", "footer")
    return buttons.build_menu(2)


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
            f" <b>to extract an Audio or Subtitle track from it.</b>"
        )
        return

    status = await sendMessage(message, "<i>Checking available Audio/Subtitle tracks...</i>")
    if not await aiopath.exists(EXTRACT_WORKDIR):
        await mkdir(EXTRACT_WORKDIR)

    file_name = media.file_name or f"{message.id}_media"
    local_path = ospath.join(EXTRACT_WORKDIR, f"{message.id}_{file_name}")
    try:
        await rply.download(local_path)
    except Exception as e:
        await editMessage(status, f"<b>Download Failed:</b> <code>{escape(str(e))}</code>")
        return

    audios, subs = await _probe_streams(local_path)
    if not audios and not subs:
        await editMessage(status, "<b>No Audio or Subtitle tracks found in this file.</b>")
        with suppress(Exception):
            await aioremove(local_path)
        return

    bot_cache[message.id] = {'path': local_path, 'audios': audios, 'subs': subs,
                              'orig_name': file_name, 'time': time()}
    await editMessage(status, "<b>Select what you want to extract:</b>",
                       _type_menu(message.from_user.id, message.id, audios, subs))


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
    await query.answer()

    if stage == 'cancel':
        with suppress(Exception):
            await aioremove(cache['path'])
        del bot_cache[msg_id]
        return await editMessage(query.message, "<b>Cancelled.</b>")

    if stage == 'back':
        return await editMessage(query.message, "<b>Select what you want to extract:</b>",
                                  _type_menu(user_id, msg_id, cache['audios'], cache['subs']))

    if stage == 'type':
        mtype = data[4]
        tracks = cache['audios'] if mtype == 'audio' else cache['subs']
        buttons = ButtonMaker()
        for t in tracks:
            label = f"{t['rel_idx'] + 1}. {t['lang']}"
            if t['title']:
                label += f" - {t['title'][:20]}"
            label += f" [{t['codec']}]"
            buttons.ibutton(label, f"extract {user_id} {msg_id} track {mtype} {t['rel_idx']}")
        buttons.ibutton("« Back", f"extract {user_id} {msg_id} back", "footer")
        buttons.ibutton("Cancel", f"extract {user_id} {msg_id} cancel", "footer")
        kind = 'Audio' if mtype == 'audio' else 'Subtitle'
        return await editMessage(query.message, f"<b>Select the {kind} track to extract:</b>", buttons.build_menu(1))

    if stage == 'track':
        mtype, rel_idx = data[4], data[5]
        fmt_map = AUDIO_FORMATS if mtype == 'audio' else SUB_FORMATS
        buttons = ButtonMaker()
        for key, (label, _) in fmt_map.items():
            buttons.ibutton(label, f"extract {user_id} {msg_id} go {mtype} {rel_idx} {key}")
        buttons.ibutton("« Back", f"extract {user_id} {msg_id} type {mtype}", "footer")
        buttons.ibutton("Cancel", f"extract {user_id} {msg_id} cancel", "footer")
        return await editMessage(query.message, "<b>Select output format:</b>", buttons.build_menu(2))

    if stage == 'go':
        mtype, rel_idx, fmt_key = data[4], int(data[5]), data[6]
        return await _do_extract(client, query, cache, mtype, rel_idx, fmt_key)


async def _do_extract(client, query, cache, mtype, rel_idx, fmt_key):
    await editMessage(query.message, "<i>Extracting, please wait...</i>")
    tracks = cache['audios'] if mtype == 'audio' else cache['subs']
    track = next((t for t in tracks if t['rel_idx'] == rel_idx), None)
    if not track:
        return await editMessage(query.message, "<b>Track not found, session may be stale.</b>")

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
        return await editMessage(query.message, f"<b>Extraction Failed:</b>\n<code>{escape(err[:300])}</code>")

    kind = 'Audio' if mtype == 'audio' else 'Subtitle'
    caption = (f"<b>{track['lang']} {label} {kind}</b>\n"
               f"<b>Extracted From:</b> <code>{escape(cache['orig_name'])}</code>")
    try:
        if mtype == 'audio':
            await client.send_audio(chat_id=query.message.chat.id, audio=out_path, caption=caption)
        else:
            await client.send_document(chat_id=query.message.chat.id, document=out_path, caption=caption)
        await editMessage(query.message, "<b>✅ Extraction Complete.</b>")
    except Exception as e:
        LOGGER.error(f"Extract upload failed: {e}")
        await editMessage(query.message, f"<b>Upload Failed:</b> <code>{escape(str(e))}</code>")
    finally:
        with suppress(Exception):
            await aioremove(out_path)


bot.add_handler(MessageHandler(extract_media_cmd, filters=command(BotCommands.ExtractCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(extract_callback, filters=regex("^extract")))
