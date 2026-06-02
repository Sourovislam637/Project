#!/usr/bin/env python3
import re
import os
from bot import user_data, LOGGER

def get_autorename(filename, user_id):
    """
    Auto Rename Logic: Cleans the filename and applies user format.
    Available Tags: {title}, {season}, {episode}, {quality}
    """
    user_dict = user_data.get(user_id, {})
    
    # যদি ইউজারের Auto Rename বন্ধ থাকে, তবে অরিজিনাল নাম রিটার্ন করবে
    if not user_dict.get('autorename', False):
        return filename

    # Default format set to {title} {season} {episode} {quality}
    format_str = user_dict.get('autorename_format', '{title} {season} {episode} {quality}')
    if not format_str:
        format_str = '{title} {season} {episode} {quality}'

    name, ext = os.path.splitext(filename)

    # তথ্য বের করা (Extracting metadata)
    season_match = re.search(r'(S\d{1,2}|Season\s*\d{1,2})', name, re.IGNORECASE)
    season = season_match.group(1) if season_match else ""

    episode_match = re.search(r'(E\d{1,3}|Ep\s*\d{1,3}|Episode\s*\d{1,3})', name, re.IGNORECASE)
    episode = episode_match.group(1) if episode_match else ""

    quality_match = re.search(r'(1080p|720p|480p|2160p|4K)', name, re.IGNORECASE)
    quality = quality_match.group(1) if quality_match else ""

    # ফাইলের নাম পরিষ্কার করা (Removing Tags and Brackets)
    clean_title = re.sub(r'\[.*?\]|\(.*?\)', '', name) 
    clean_title = re.sub(r'(S\d{1,2}|E\d{1,3}|1080p|720p|480p|2160p|4K|x264|x265|10bit|BluRay|WEB-DL|WEBRip|Multi|Audio|ESub|HEVC)', '', clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r'(\s|-|\.)+', ' ', clean_title).strip() 

    try:
        # ইউজারের ফরম্যাট অনুযায়ী নাম সাজানো
        new_name = format_str.format(
            title=clean_title,
            season=season,
            episode=episode,
            quality=quality
        )
        
        # তৈরি হওয়া ডাবল স্পেস ক্লিন করা
        new_name = re.sub(r'\s+', ' ', new_name).strip()
        
        # যদি নতুন নাম খালি হয়ে যায়, তবে ব্যাকআপ হিসেবে ক্লিন টাইটেল দিবে
        if not new_name:
            new_name = clean_title
            
        LOGGER.info(f"Auto Renamed: {filename} -> {new_name}{ext}")
        return f"{new_name}{ext}"
    
    except KeyError as e:
        LOGGER.error(f"Auto Rename KeyError: Missing tag {e} in user format.")
        return filename
