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
    RSS_FEEDS = {
        'subplease': "https://subsplease.org/rss/?r=1080",
        'test_rss': "https://web-production-71c2a.up.railway.app/rss/AEYuGTeOGkhz1FGtDZUzwQ"
    }

    user_dict = user_data.get(user_id, {})
    seen_rss = user_dict.get('seen_rss')

    is_initial = seen_rss is None
    if is_initial:
        seen_rss = []

    for feed_name, feed_url in RSS_FEEDS.items():
        if not rss_pref.get(feed_name):
            continue

        if feed_url not in feed_cache:
            try:
                feed = await sync_to_async(feedparser.parse, feed_url)
                feed_cache[feed_url] = feed
            except Exception as e:
                LOGGER.error(f"RSS Fetch Error for {feed_url}: {e}")
                continue
        else:
            feed = feed_cache[feed_url]

        if not feed or not feed.entries:
            continue

        if is_initial:
            seen_rss.extend([entry.link for entry in feed.entries])
            continue

        new_entries = [entry for entry in feed.entries if entry.link not in seen_rss]
        if not new_entries:
            continue

        # Process oldest first
        new_entries.reverse()

        for entry in new_entries:
            LOGGER.info(f"New RSS item for {user_id} from {feed_name}: {entry.title}")
            mock_id = int(time() * 1000)
            msg_text = f"/leech {entry.link}"

            if rss_chat := rss_pref.get('chat'):
                msg_text += f" -ud {rss_chat}"
            if rss_thumb := rss_pref.get('thumb'):
                msg_text += f" -t {rss_thumb}"
            if rss_pre := rss_pref.get('prefix'):
                msg_text += f" -pre {rss_pre}"
            if rss_suf := rss_pref.get('suffix'):
                msg_text += f" -suf {rss_suf}"
            if rss_cap := rss_pref.get('caption'):
                msg_text += f" -cap {rss_cap}"
            if rss_ar := rss_pref.get('autorename'):
                msg_text += f" -ar {rss_ar}"

            mock_msg = MockMessage(user_id, msg_text, mock_id)

            try:
                await _mirror_leech(bot, mock_msg, isLeech=True)
                seen_rss.append(entry.link)
            except Exception as e:
                LOGGER.error(f"Failed to start RSS task for {user_id}: {e}")

            await sleep(5)

    if is_initial:
        update_user_ldata(user_id, 'seen_rss', seen_rss)
        if DATABASE_URL:
            await DbManger().update_user_data(user_id)
        return

    # Keep seen_rss reasonably sized
    if len(seen_rss) > 500:
        seen_rss = seen_rss[-500:]

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
    scheduler.add_job(rss_monitor, 'interval', minutes=3, id='rss_monitor', replace_existing=True)
    LOGGER.info("RSS Monitor Scheduled to run every 10 minutes.")
