import feedparser
from asyncio import sleep
from time import time

from bot import scheduler, user_data, LOGGER, bot, DATABASE_URL
from bot.helper.ext_utils.bot_utils import new_task, update_user_ldata, sync_to_async
from bot.helper.ext_utils.db_handler import DbManger
from bot.modules.mirror_leech import _mirror_leech

class MockMessage:
    def __init__(self, uid, text, mid):
        self.from_user = type('User', (), {'id': uid, 'username': None, 'mention': f'ID:{uid}', 'is_bot': False})
        self.chat = type('Chat', (), {'id': uid})
        self.text = text
        self.id = mid
        self.reply_to_message = None
        self.sender_chat = None

    async def reply(self, text, *args, **kwargs):
        return await bot.send_message(self.chat.id, text, *args, **kwargs)

    async def reply_text(self, text, *args, **kwargs):
        return await bot.send_message(self.chat.id, text, *args, **kwargs)

    async def delete(self):
        pass

    async def reply_photo(self, photo, caption=None, *args, **kwargs):
        return await bot.send_photo(self.chat.id, photo, caption=caption, *args, **kwargs)

async def check_user_rss(user_id, rss_pref, feed_cache):
    if not rss_pref.get('subplease'):
        return

    feed_url = "https://subsplease.org/rss/?r=1080"

    if feed_url not in feed_cache:
        try:
            feed = await sync_to_async(feedparser.parse, feed_url)
            feed_cache[feed_url] = feed
        except Exception as e:
            LOGGER.error(f"RSS Fetch Error for {feed_url}: {e}")
            return
    else:
        feed = feed_cache[feed_url]

    if not feed or not feed.entries:
        return

    user_dict = user_data.get(user_id, {})
    seen_rss = user_dict.get('seen_rss')

    if seen_rss is None:
        seen_rss = [entry.link for entry in feed.entries]
        update_user_ldata(user_id, 'seen_rss', seen_rss)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
        return

    new_entries = []
    for entry in feed.entries:
        if entry.link not in seen_rss:
            new_entries.append(entry)

    if not new_entries:
        return

    # Process oldest first
    new_entries.reverse()

    for entry in new_entries:
        LOGGER.info(f"New RSS item for {user_id}: {entry.title}")
        mock_id = int(time() * 1000)
        msg_text = f"/leech {entry.link}"
        mock_msg = MockMessage(user_id, msg_text, mock_id)

        try:
            await _mirror_leech(bot, mock_msg, isLeech=True)
            seen_rss.append(entry.link)
        except Exception as e:
            LOGGER.error(f"Failed to start RSS task for {user_id}: {e}")

        await sleep(5)

    # Keep seen_rss reasonably sized
    if len(seen_rss) > 200:
        seen_rss = seen_rss[-200:]

    update_user_ldata(user_id, 'seen_rss', seen_rss)
    if DATABASE_URL:
        await DbManger().update_user_data(user_id)

async def rss_monitor():
    if not user_data:
        return

    feed_cache = {}
    for user_id, data in list(user_data.items()):
        if not isinstance(user_id, int):
            continue
        rss_pref = data.get('rss')
        if rss_pref:
            await check_user_rss(user_id, rss_pref, feed_cache)

if scheduler:
    scheduler.add_job(rss_monitor, 'interval', minutes=10, id='rss_monitor', replace_existing=True)
    LOGGER.info("RSS Monitor Scheduled to run every 10 minutes.")
