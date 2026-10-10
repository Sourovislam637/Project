"""Recovery helpers for Telegram transfers that hang (0 B/s forever).

With wzgram a media session can die or half-open; every later transfer through it then
sits at 0% until the dyno is restarted. Two small tools:
  * reset_media_sessions(): drop media sessions that are really stopped
  * run_guarded(): run a transfer and abort it when no progress callback fired for `stall` s
"""
from asyncio import CancelledError, create_task, sleep, wait, wait_for
from os import environ
from time import time

from bot import bot, user, LOGGER

STALL_TIMEOUT = int(environ.get('TG_STALL_TIMEOUT', '420') or 420)   # seconds without progress


async def reset_media_sessions(*clients):
    for c in {id(x): x for x in (clients or (bot, user)) if x}.values():
        try:
            sessions = getattr(c, 'media_sessions', None)
            if not sessions:
                continue
            for dc, ss in list(sessions.items()):
                started = getattr(ss, 'is_started', None)
                if started is not None and hasattr(started, 'is_set') and started.is_set():
                    continue
                try:
                    await wait_for(ss.stop(), 10)
                except Exception:
                    pass
                sessions.pop(dc, None)
        except Exception as e:
            LOGGER.warning(f"media session reset failed: {e!r}")


async def run_guarded(factory, progress, is_cancelled=lambda: False, stall=STALL_TIMEOUT, name='transfer'):
    """factory() -> coroutine. `progress` is a dict whose 't' key the progress callback refreshes.
    Raises ConnectionError (after cancelling the transfer) when it stalls."""
    progress['t'] = time()
    task = create_task(factory())
    try:
        while True:
            done, _ = await wait({task}, timeout=20)
            if done:
                return task.result()
            if is_cancelled():
                continue  # the transfer raises StopTransmission by itself
            if time() - progress['t'] > stall:
                LOGGER.error(f"{name} stalled for {stall}s with no progress - aborting it")
                task.cancel()
                try:
                    await task
                except BaseException:
                    pass
                await reset_media_sessions()
                raise ConnectionError(f"{name} stalled (no progress for {stall}s)")
    except CancelledError:
        task.cancel()
        raise
