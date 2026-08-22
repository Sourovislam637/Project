#!/usr/bin/env python3
"""
/merge command.

Reply to a video with /merge, then just send (no reply needed) any number
of Audio and/or Subtitle files you want combined with it, in any order,
and tap Done when finished. If at least one Audio file was added, you'll
then be asked to choose:
    Merger 1 - Replace : drops every existing audio track, keeps only the
               audio you sent (subtitles - both original and newly added -
               are kept).
    Merger 2 - Add     : keeps every existing audio track, and adds your
               audio as extra track(s) - along with any added subtitles.
If only subtitles were added (no audio), they're simply added alongside
everything that's already there.
In all cases, when audio is added, the first added track is placed first
and marked as the default, so Telegram's built-in player selects it
automatically. Download and upload both show a live progress bar, same
look as the Leech DL/Up status.
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
from bot.helper.ext_utils.simple_progress import ProgressTracker

MERGE_WORKDIR = "Merged"
SESSION_TIMEOUT = 600  # seconds a merge session (collecting files / waiting for the button tap) stays valid
SUBTITLE_EXTS = ('.srt', '.ass', '.ssa', '.vtt')

merge_waiting = {}  # user_id -> the /merge command message id we're actively collecting files for


def _is_audio_msg(event):
    return bool(event.audio or event.voice
                or (event.document and (event.document.mime_type or '').startswith('audio')))


def _is_subtitle_msg(event):
    doc = event.document
    return bool(doc and doc.file_name and doc.file_name.lower().endswith(SUBTITLE_EXTS))


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


def _collect_buttons(user_id, msg_id):
    buttons = ButtonMaker()
    buttons.ibutton("✅ Done", f"merge {user_id} {msg_id} done")
    buttons.ibutton("Cancel", f"merge {user_id} {msg_id} cancel", "footer")
    return buttons.build_menu(2)


def _collect_text(cache):
    a, s = len(cache['added_audios']), len(cache['added_subs'])
    return ("<b>Send Audio and/or Subtitle files to add - as many as you like, no need to reply to anything.</b>\n\n"
            f"<b>Added So Far :</b> {a} Audio, {s} Subtitle\n\n"
            "<i>Tap Done when finished.</i>")


@new_task
async def merge_cmd(client, message):
    rply = message.reply_to_message
    video = rply and next((m for m in [rply.video, rply.document] if m is not None), None)
    if not video:
        await sendMessage(
            message,
            f"<b>Reply to a Video file with</b> <code>/{BotCommands.MergeCommand[0]}</code>"
            f" <b>to add/replace Audio or add Subtitle tracks in it.</b>"
        )
        return

    user_id = message.from_user.id
    status = await sendMessage(message, "<i>Downloading video...</i>")
    if not await aiopath.exists(MERGE_WORKDIR):
        await mkdir(MERGE_WORKDIR)

    video_name = video.file_name or f"{message.id}_video"
    video_path = ospath.join(MERGE_WORKDIR, f"{message.id}_v_{video_name}")
    tracker = ProgressTracker(status, "📥 Downloading Video", video_name)
    try:
        await rply.download(video_path, progress=tracker)
    except Exception as e:
        await editMessage(status, f"<b>Download Failed:</b> <code>{escape(str(e))}</code>")
        return

    cache = {'video_path': video_path, 'video_name': video_name,
             'added_audios': [], 'added_subs': [], 'prompt_msg': status, 'time': time()}
    bot_cache[message.id] = cache
    await editMessage(status, _collect_text(cache), _collect_buttons(user_id, message.id))

    merge_waiting[user_id] = message.id

    async def item_filter(_, __, event):
        u = event.from_user or event.sender_chat
        return bool(u and u.id == user_id and event.chat.id == message.chat.id
                    and merge_waiting.get(user_id) == message.id
                    and (_is_audio_msg(event) or _is_subtitle_msg(event)))

    handler = client.add_handler(MessageHandler(_on_item_received, filters=create(item_filter)), group=-1)
    start = time()
    while merge_waiting.get(user_id) == message.id:
        await sleep(1)
        if time() - start > SESSION_TIMEOUT:
            merge_waiting.pop(user_id, None)
            leftover = bot_cache.pop(message.id, None)
            if leftover:
                await _cleanup(leftover)
            with suppress(Exception):
                await editMessage(status, "<b>⏱ Timed Out.</b>")
            break
    client.remove_handler(*handler)


@new_task
async def _on_item_received(client, message):
    user_id = message.from_user.id
    msg_id = merge_waiting.get(user_id)
    if not msg_id or msg_id not in bot_cache:
        return
    cache = bot_cache[msg_id]
    cache['time'] = time()

    is_sub = _is_subtitle_msg(message)
    kind = 'Subtitle' if is_sub else 'Audio'
    media = message.document if is_sub else (message.audio or message.voice or message.document)
    fname = getattr(media, 'file_name', None) or f"{message.id}_{kind.lower()}"

    dl_status = await sendMessage(message, f"<i>Downloading {kind}...</i>")
    bucket = cache['added_subs'] if is_sub else cache['added_audios']
    prefix = 's' if is_sub else 'a'
    item_path = ospath.join(MERGE_WORKDIR, f"{msg_id}_{prefix}{len(bucket)}_{fname}")
    tracker = ProgressTracker(dl_status, f"📥 Downloading {kind}", fname)
    try:
        await message.download(item_path, progress=tracker)
    except Exception as e:
        await editMessage(dl_status, f"<b>Download Failed:</b> <code>{escape(str(e))}</code>")
        return

    bucket.append({'path': item_path, 'name': fname})
    await editMessage(dl_status, f"<b>✅ Added {kind}:</b> <code>{escape(fname)}</code>")
    with suppress(Exception):
        await editMessage(cache['prompt_msg'], _collect_text(cache), _collect_buttons(user_id, msg_id))


@new_task
async def merge_callback(client, query):
    data = query.data.split()
    user_id, msg_id, stage = int(data[1]), int(data[2]), data[3]

    if query.from_user.id != user_id and not await CustomFilters.sudo(client, query):
        return await query.answer("This is not for you!", show_alert=True)

    cache = bot_cache.get(msg_id)
    if not cache:
        return await query.answer("Session expired, please send the command again.", show_alert=True)
    if time() - cache['time'] > SESSION_TIMEOUT:
        merge_waiting.pop(user_id, None)
        await _cleanup(cache)
        bot_cache.pop(msg_id, None)
        return await editMessage(query.message, "<b>⏱ Timed Out. Please send the command again.</b>")
    cache['time'] = time()

    if stage == 'cancel':
        await query.answer()
        merge_waiting.pop(user_id, None)
        await _cleanup(cache)
        bot_cache.pop(msg_id, None)
        return await editMessage(query.message, "<b>Cancelled.</b>")

    if stage == 'done':
        if not cache['added_audios'] and not cache['added_subs']:
            return await query.answer("Send at least one Audio or Subtitle file first!", show_alert=True)
        await query.answer()
        merge_waiting.pop(user_id, None)  # stop accepting more files once we move to processing

        if not cache['added_audios']:
            # Only subtitles were added - nothing to replace, just merge them in.
            return await _do_merge(query, cache, msg_id, 'add')

        buttons = ButtonMaker()
        buttons.ibutton("🔁 Merger 1 (Replace Audio)", f"merge {user_id} {msg_id} do replace")
        buttons.ibutton("➕ Merger 2 (Add Audio, Keep Existing)", f"merge {user_id} {msg_id} do add")
        buttons.ibutton("Cancel", f"merge {user_id} {msg_id} cancel", "footer")
        return await editMessage(
            query.message,
            "<b>Merger 1</b> : Replaces all existing Audio tracks with the Audio you sent.\n\n"
            "<b>Merger 2</b> : Keeps every existing Audio track, and adds your Audio as extra track(s).\n\n"
            "<i>Any Subtitles you added are kept in both modes, and the first added Audio track plays "
            "by default in Telegram.</i>\n\n"
            "Click the Button of your choice ⟱⟱",
            buttons.build_menu(1)
        )

    if stage == 'do':
        return await _do_merge(query, cache, msg_id, data[4])


async def _cleanup(cache):
    with suppress(Exception):
        await aioremove(cache['video_path'])
    for item in cache['added_audios'] + cache['added_subs']:
        with suppress(Exception):
            await aioremove(item['path'])


async def _do_merge(query, cache, msg_id, mode):
    await editMessage(query.message, "<i>Merging, please wait...</i>")
    video_path = cache['video_path']
    added_audios, added_subs = cache['added_audios'], cache['added_subs']
    src_base = ospath.splitext(cache['video_name'])[0]
    out_path = ospath.join(MERGE_WORKDIR, f"{src_base}_merged.mkv")

    # Input order: video, then every added audio, then every added subtitle.
    inputs = [video_path] + [a['path'] for a in added_audios] + [s['path'] for s in added_subs]
    audio_input_start = 1
    sub_input_start = 1 + len(added_audios)

    base_cmd = [bot_cache['pkgs'][2], "-hide_banner", "-loglevel", "error"]
    for inp in inputs:
        base_cmd += ["-i", inp]

    base_cmd += ["-map", "0:v"]
    for i in range(len(added_audios)):
        base_cmd += ["-map", f"{audio_input_start + i}:a"]
    if mode == 'add':
        base_cmd += ["-map", "0:a?"]
    base_cmd += ["-map", "0:s?"]
    for i in range(len(added_subs)):
        base_cmd += ["-map", f"{sub_input_start + i}:0"]

    if added_audios:
        base_cmd += ["-disposition:a:0", "default"]
        if mode == 'add':
            existing_audio = await _count_audio_streams(video_path)
            for i in range(1, existing_audio + 1):
                base_cmd += [f"-disposition:a:{len(added_audios) - 1 + i}", "0"]
        for i, a in enumerate(added_audios):
            base_cmd += [f"-metadata:s:a:{i}", f"title={ospath.splitext(a['name'])[0][:40]}"]

    async def run(codec_args):
        cmd = base_cmd + codec_args + [out_path]
        proc = await create_subprocess_exec(*cmd, stderr=PIPE)
        code = await proc.wait()
        err = (await proc.stderr.read()).decode().strip() if code != 0 else ""
        return code == 0 and await aiopath.exists(out_path), err

    ok, err = await run(["-c", "copy"])
    if not ok:
        # An added Audio's codec/sample-format sometimes can't be pure
        # stream-copied alongside the source; retry once re-encoding just
        # the audio to AAC (which Matroska always accepts).
        LOGGER.warning(f"Merge stream-copy failed, retrying with AAC re-encode: {err}")
        with suppress(Exception):
            await aioremove(out_path)
        ok, err = await run(["-c:v", "copy", "-c:a", "aac", "-c:s", "copy"])

    if not ok:
        LOGGER.error(f"Merge failed: {err}")
        await editMessage(query.message, f"<b>Merge Failed:</b>\n<code>{escape(err[:300])}</code>")
        await _cleanup(cache)
        bot_cache.pop(msg_id, None)
        return

    up_status = await query.message.reply(f"<i>Uploading {escape(ospath.basename(out_path))}...</i>")
    tracker = ProgressTracker(up_status, "📤 Uploading", ospath.basename(out_path))
    try:
        await query.message.reply_video(video=out_path, caption=f"<b>Merged:</b> <code>{escape(src_base)}</code>",
                                          progress=tracker)
        await editMessage(up_status, "<b>✅ Merge Complete.</b>")
        await editMessage(query.message, "<b>✅ Merge Complete.</b>")
    except Exception as e:
        LOGGER.error(f"Merge upload failed: {e}")
        await editMessage(up_status, f"<b>Upload Failed:</b> <code>{escape(str(e))}</code>")
    finally:
        with suppress(Exception):
            await aioremove(out_path)
        await _cleanup(cache)
        bot_cache.pop(msg_id, None)


bot.add_handler(MessageHandler(merge_cmd, filters=command(BotCommands.MergeCommand) & CustomFilters.authorized & ~CustomFilters.blacklisted))
bot.add_handler(CallbackQueryHandler(merge_callback, filters=regex("^merge")))
