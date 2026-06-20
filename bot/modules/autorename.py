#!/usr/bin/env python3
import re
import os
from bot import user_data, LOGGER, bot
from pyrogram.handlers import MessageHandler
from pyrogram.filters import command
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.button_build import ButtonMaker
from html import escape

def trun(text, limit=60):
    text = str(text)
    return text[:limit] + "..." if len(text) > limit else text

def get_autorename(filename, user_id, size="", media_quality="", lang="", subs=""):
    """
    Advanced Auto Rename Logic: Cleans the filename and applies user format.
    Available Tags: {title}, {season}, {episode}, {quality}, {codec}, {audio}, {sub}, {size}, {language}
    """
    user_dict = user_data.get(user_id, {})
    
    # যদি ইউজারের Auto Rename বন্ধ থাকে, তবে অরিজিনাল নাম রিটার্ন করবে
    if not user_dict.get('autorename', False):
        return filename

    # Default format set
    format_str = user_dict.get('autorename_format', '{title} - S{season}E{episode} - {quality} {codec} {audio} {sub}')
    if not format_str:
        format_str = '{title} - S{season}E{episode} - {quality}'

    name, ext = os.path.splitext(filename)

    # তথ্য বের করা (শুধুমাত্র সংখ্যা বের করা হবে যাতে S{season}E{episode} কাস্টমাইজ করা যায়)
    season_match = re.search(r'(?:S|Season\s*)(\d{1,2})', name, re.IGNORECASE)
    season = season_match.group(1).zfill(2) if season_match else ""

    episode_match = re.search(r'(?:E|Ep|Episode\s*)(\d{1,3})', name, re.IGNORECASE)
    episode = episode_match.group(1).zfill(2) if episode_match else ""

    quality_match = re.search(r'(480p|720p|1080p|1440p|2160p|4K)', name, re.IGNORECASE)
    quality = quality_match.group(1) if quality_match else media_quality
    
    codec_match = re.search(r'(x264|x265|HEVC|AV1|H264|H265|10bit|10Bit|AVC)', name, re.IGNORECASE)
    codec = codec_match.group(1) if codec_match else ""
    
    audio_match = re.search(r'(Dual[\s\-]?Audio|Multi[\s\-]?Audio|Hindi|English|Tamil|Telugu|Malayalam|Kannada|Bengali)', name, re.IGNORECASE)
    audio = audio_match.group(1).title() if audio_match else lang
    
    sub_match = re.search(r'(ESub|HC-ENG|MSub|Multi[\s\-]?Sub|Subbed)', name, re.IGNORECASE)
    sub = sub_match.group(1) if sub_match else subs

    # ফাইলের নাম পরিষ্কার করা (Cleaning the Original Name & Brackets)
    clean_title = re.sub(r'\[.*?\]|\(.*?\)', '', name) 
    noise_pattern = r'(S\d{1,2}|E\d{1,3}|Ep\s*\d{1,3}|Episode\s*\d{1,3}|480p|720p|1080p|1440p|2160p|4K|x264|x265|HEVC|AV1|H264|H265|10bit|10Bit|AVC|BluRay|WEB-DL|WEBRip|HDRip|HDTV|Dual[\s\-]?Audio|Multi[\s\-]?Audio|Hindi|English|Tamil|Telugu|Malayalam|Kannada|Bengali|ESub|HC-ENG|MSub|Multi[\s\-]?Sub|Subbed|Audio)'
    clean_title = re.sub(noise_pattern, '', clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r'(\s|-|\.)+', ' ', clean_title).strip() 

    # ইউজারের Custom Title চেক করা
    custom_title = user_dict.get('custom_title', '')
    final_title = custom_title if custom_title else clean_title

    try:
        # ইউজারের ফরম্যাট অনুযায়ী নাম সাজানো
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
        
        # যদি ফাইলে সিজন বা এপিসোড না থাকে, তবে ফাঁকা 'SE' মুছে ফেলা
        if not season and not episode:
            new_name = new_name.replace('SE', '').replace('S E', '')
        elif not season and episode:
            new_name = new_name.replace('SE', 'E')
            
        # তৈরি হওয়া এক্সট্রা স্পেস, ড্যাশ বা ডট ক্লিন করা (Safeguard)
        new_name = re.sub(r'\s+', ' ', new_name)
        new_name = re.sub(r'-\s*-', '-', new_name)
        new_name = re.sub(r'\.\s*\.', '.', new_name)
        new_name = new_name.strip(' -.')
        
        # যদি কোনো কারণে নতুন নাম খালি হয়ে যায়, তবে ব্যাকআপ হিসেবে টাইটেল দিবে
        if not new_name:
            new_name = final_title
            
        LOGGER.info(f"Auto Renamed: {filename} -> {new_name}{ext}")
        return f"{new_name}{ext}"
    
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
    text += f"➲ <b>Format Example :</b> <code>{{title}} - S{{season}}E{{episode}} - {{quality}} [{{size}}]</code>\n\n"
    text += f"➲ <b>Description :</b> <i>Set your Custom Format and Title for Auto Renaming files. Custom Title will override {{title}}.</i>"

    buttons.ibutton("Disable" if auto_status == 'Enabled' else "Enable", f"userset {user_id} toggle_autorename")
    buttons.ibutton("Set Format", f"userset {user_id} autorename_format edit")
    buttons.ibutton("Set Custom Title", f"userset {user_id} custom_title edit")
    
    if format_str != 'Not Exists':
        buttons.ibutton("↻ Delete Format", f"userset {user_id} dautorename_format")
    if custom_title != 'Not Exists':
        buttons.ibutton("↻ Delete Title", f"userset {user_id} dcustom_title")
    
    # Back button removed as requested, only Close remains.
    buttons.ibutton("Close", f"userset {user_id} close", "footer")
    
    button = buttons.build_menu(2)
    await sendMessage(message, text, button)

# Command Handler
bot.add_handler(MessageHandler(autorename_cmd, filters=command("autorename") & CustomFilters.authorized_uset))
