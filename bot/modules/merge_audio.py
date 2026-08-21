#!/usr/bin/env python3
"""
/merge command.

Reply to a video with /merge, then send the audio file you want combined
with it. Two modes are then offered:
    Merger 1 - Replace : drops every existing audio track, keeps only the
               audio you just sent (subtitles are kept).
    Merger 2 - Add     : keeps every existing audio track and subtitle,
               and adds your audio as an extra track.
In both modes the added audio is mapped first and marked as the default
track, so Telegram's built-in player selects it automatically.
"""
from os import path as ospath
from time import time
from html import escape
from json import loads as jloads
from contextlib import suppress
from asyncio import create_subprocess_exec, sleep
from asyncio.subprocess import PIPE

from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from pyrogram.filters import command, regex, create
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import bot, bot_cache, LOGGER
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.ext_utils.bot_utils import cmd_exec, new_task

MERGE_WORKDIR = "Merged"
MERGE_TIMEOUT = 300       # seconds a merge session (waiting for the button tap) stays valid
AUDIO_WAIT_TIMEOUT = 120  # seconds to wait for the user to send the audio file

merge_waiting = {}  # user_id -> the /merge command message id we're waiting on


async def _count_audio_streams(path):
    stdout, stderr, code = await cmd_exec(["ffprobe", "-hide_banner", "-loglevel", "error",
                                            "-print_format", "json", "-show_streams", path])
    if code != 0 or not stdout:
        LOGGER.error(f"Merge: ffprobe failed for {path} : {stderr}")
        return 0
    try:
        streams = jloads(stdout).get('streams', [])
    except Exception as e:
        LOGGER.error(f"Merge: ffprobe json parse error: {e}")
        return 0
    return sum(1 for s in streams if s.get('codec_type') == 'audio')


@new_task
async def merge_cmd(client, message):
    rply = message.reply_to_message
    video = rply and next((m for m in [rply.video, rply.document] if m is not None), None)
    if not video:
        await sendMessage(
            message,
            f"<b>Reply to a Video file with</b> <code>/{BotCommands.MergeCommand[0]}</code>"
            f" <b>to add/replace an Audio track in it.</b>"
        )
        return

    user_id = message.from_user.id
    status = await sendMessage(message, "<i>Downloading video...</i>")
    if not await aiopath.exists(MERGE_WORKDIR):
        await mkdir(MERGE_WORKDIR)

    video_name = video.file_name or f"{message.id}_video"
    video_path = ospath.join(MERGE_WORKDIR, f"{message.id}_v_{video_name}")
    try:
        await rply.download(video_path)
    except Exception as e:
        await editMessage(status, f"<b>Download Failed:</b> <code>{escape(str(e))}</code>")
        return

    bot_cache[message.id] = {'video_path': video_path, 'video_name': video_name,
                              'audio_path': None, 'time': time()}
    await editMessage(status, "<b>Now send the Audio file you want to merge (as a reply here).</b>\n"
                               "<i>Waiting up to 2 minutes...</i>")

    merge_waiting[user_id] = message.id

    async def audio_filter(_, __, event):
        u = event.from_user or event.sender_chat
        return bool(u and u.id == user_id and event.chat.id == message.chat.id
                    and merge_waiting.get(user_id) == message.id
                    and (event.audio or event.voice
                         or (event.document and (event.document.mime_type or '').startswith('audio'))))

    handler = client.add_handler(MessageHandler(_on_audio_received, filters=create(audio_filter)), group=-1)
    start = time()
    while merge_waiting.get(user_id) == message.id:
        await sleep(0.5)
        if time() - start > AUDIO_WAIT_TIMEOUT:
            merge_waiting.pop(user_id, None)
            cache = bot_cache.pop(message.id, None)
            if cache:
                with suppress(Exception):
                    await aioremove(cache['video_path'])
            await editMessage(status, "<b>⏱ Timed Out waiting for the Audio file.</b>")
            break
    client.remove_handler(*handler)


@new_task
async def _on_audio_received(client, message):
    user_id = message.from_user.id
    msg_id = merge_waiting.get(user_id)
    if not msg_id or msg_id not in bot_cache:
        return
    merge_waiting.pop(user_id, None)
    cache = bot_cache[msg_id]
    cache['time'] = time()

    status = await sendMessage(message, "<i>Downloading audio...</i>")
    audio_media = message.audio or message.voice or message.document
    audio_name = getattr(audio_media, 'file_name', None) or f"{message.id}_audio"
    audio_path = ospath.join(MERGE_WORKDIR, f"{msg_id}_a_{audio_name}")
    try:
        await message.download(audio_path)
    except Exception as e:
        await editMessage(status, f"<b>Download Failed:</b> <code>{escape(str(e))}</code>")
        return
    cache['audio_path'] = audio_path

    buttons = ButtonMaker()
    buttons.ibutton("🔁 Merger 1 (Replace Audio)", f"merge {user_id} {msg_id} do replace")
    buttons.ibutton("➕ Merger 2 (Add Audio, Keep Existing)", f"merge {user_id} {msg_id} do add")
    buttons.ibutton("Cancel", f"merge {user_id} {msg_id} cancel", "footer")
    await editMessage(
        status,
        "<b>Merger 1</b> : Replaces all existing Audio tracks with the Audio you just sent.\n\n"
        "<b>Merger 2</b> : Keeps every existing Audio track and Subtitle, and adds your Audio as "
        "an extra track.\n\n"
        "<i>In both modes, the added Audio track plays by default in Telegram.</i>\n\n"
        "Click the Button of your choice ⟱⟱",
        buttons.build_menu(1)
    )


@new_task
async def merge_callback(client, query):
    data = query.data.split()
    user_id, msg_id, stage = int(data[1]), int(data[2]), data[3]

    if query.from_user.id != user_id and not await CustomFilters.sudo(client, query):
        return await query.answer("This is not for you!", show_alert=True)

    cache = bot_cache.get(msg_id)
    if not cache or not cache.get('audio_path'):
        return await query.answer("Session expired, please send the command again.", show_alert=True)
    if time() - cache['time'] > MERGE_TIMEOUT:
        await _cleanup(cache, msg_id)
        return await editMessage(query.message, "<b>⏱ Timed Out. Please send the command again.</b>")

    await query.answer()

    if stage == 'cancel':
        await _cleanup(cache, msg_id)
        return await editMessage(query.message, "<b>Cancelled.</b>")

    if stage == 'do':
        return await _do_merge(query, cache, msg_id, data[4])


async def _cleanup(cache, msg_id):
    with suppress(Exception):
        await aioremove(cache['video_path'])
    if cache.get('audio_path'):
        with suppress(Exception):
            await aioremove(cache['audio_path'])
    bot_cache.pop(msg_id, None)


async def _do_merge(query, cache, msg_id, mode):
    await editMessage(query.message, "<i>Merging, please wait...</i>")
    video_path, audio_path = cache['video_path'], cache['audio_path']
    src_base = ospath.splitext(cache['video_name'])[0]
    out_path = ospath.join(MERGE_WORKDIR, f"{src_base}_merged.mkv")

    base_cmd = [bot_cache['pkgs'][2], "-hide_banner", "-loglevel", "error",
                "-i", video_path, "-i", audio_path, "-map", "0:v"]
    if mode == 'replace':
        base_cmd += ["-map", "1:a", "-map", "0:s?", "-disposition:a:0", "default"]
    else:
        existing_audio = await _count_audio_streams(video_path)
        base_cmd += ["-map", "1:a", "-map", "0:a?", "-map", "0:s?", "-disposition:a:0", "default"]
        for i in range(1, existing_audio + 1):
            base_cmd += [f"-disposition:a:{i}", "0"]

    async def run(codec_args):
        cmd = base_cmd + codec_args + ["-metadata:s:a:0", "title=Added Audio", out_path]
        proc = await create_subprocess_exec(*cmd, stderr=PIPE)
        code = await proc.wait()
        err = (await proc.stderr.read()).decode().strip() if code != 0 else ""
        return code == 0 and await aiopath.exists(out_path), err

    ok, err = await run(["-c", "copy"])
    if not ok:
        # The added audio's codec/sample-format is sometimes incompatible for
        # a pure stream-copy alongside the source; retry once re-encoding
        # just the audio to AAC (which Matroska always accepts).
        LOGGER.warning(f"Merge stream-copy failed, retrying with AAC re-encode: {err}")
        with suppress(Exception):
            await aioremove(out_path)
        ok, err = await run(["-c:v", "copy", "-c:a", "aac", "-c:s", "copy"])

    if not ok:
        LOGGER.error(f"Merge failed: {err}")
        await editMessage(query.message, f"<b>Merge Failed:</b>\n<code>{escape(err[:300])}</code>")
        await _cleanup(cache, msg_id)
        return

    try:
        await query.message.reply_video(video=out_path, caption=f"<b>Merged:</b> <code>{escape(src_base)}</code>")
        await editMessage(query.message, "<b>✅ Merge Complete.</b>")
    except Exception as e:
        LOGGER.error(f"Merge upload failed: {e}")
        await editMessage(query.message, f"<b>Upload Failed:</b> <code>{escape(str(e))}</code>")
    finally:
        with suppress(Exception):
            await aioremove(out_path)
        await _cleanup(cache, msg_id)


bot.add_handler(MessageHandler(merge_cmd, filters=command(BotCommands.MergeCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(merge_callback, filters=regex("^merge")))
