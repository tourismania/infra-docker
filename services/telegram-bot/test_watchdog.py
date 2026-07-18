"""Тесты watchdog из issue #22/#16. Запуск: python3 -m unittest test_watchdog -v
(из services/telegram-bot/). Никаких новых зависимостей — только stdlib
и python-telegram-bot, который уже установлен для самого бота.
"""
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:test-token")
os.environ.setdefault("TELEGRAM_BOT_ADMIN_CHAT_ID", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import telegram_bot as tb  # noqa: E402


def fake_do_request(status_code):
    async def _inner(self, *args, **kwargs):
        return status_code, b"{}"
    return _inner


def make_ctx(failures=0):
    ctx = mock.MagicMock()
    ctx.application.bot_data = {"watchdog_failures": failures}
    return ctx


class GetUpdatesFreshnessTrackerTest(unittest.IsolatedAsyncioTestCase):
    async def test_updates_timestamp_on_http_200(self):
        tracker = tb._GetUpdatesFreshnessTracker(connect_timeout=1, read_timeout=1, pool_timeout=1)
        before = time.monotonic()
        with mock.patch.object(tb.HTTPXRequest, "do_request", fake_do_request(200)):
            await tracker.do_request("https://example", "POST")
        self.assertGreaterEqual(tb._last_get_updates_at, before)

    async def test_ignores_non_200_response(self):
        tb._last_get_updates_at = time.monotonic() - 500
        before = tb._last_get_updates_at
        tracker = tb._GetUpdatesFreshnessTracker(connect_timeout=1, read_timeout=1, pool_timeout=1)
        with mock.patch.object(tb.HTTPXRequest, "do_request", fake_do_request(409)):
            await tracker.do_request("https://example", "POST")
        self.assertEqual(tb._last_get_updates_at, before)


class WatchdogCheckTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.exit_calls = []
        self._orig_exit = os._exit

        def fake_exit(code):
            self.exit_calls.append(code)
            raise SystemExit(code)

        os._exit = fake_exit

    def tearDown(self):
        os._exit = self._orig_exit

    async def test_stays_healthy_when_getupdates_fresh(self):
        tb._last_get_updates_at = time.monotonic()
        ctx = make_ctx(failures=2)
        await tb.watchdog_check(ctx)
        self.assertEqual(ctx.application.bot_data["watchdog_failures"], 0)
        self.assertEqual(self.exit_calls, [])

    async def test_single_blip_does_not_restart(self):
        tb._last_get_updates_at = time.monotonic() - (tb.WATCHDOG_GETUPDATES_MAX_AGE_SECONDS + 1)
        ctx = make_ctx()
        await tb.watchdog_check(ctx)
        self.assertEqual(ctx.application.bot_data["watchdog_failures"], 1)
        self.assertEqual(self.exit_calls, [])

    async def test_exits_after_max_failures_when_stale(self):
        tb._last_get_updates_at = time.monotonic() - (tb.WATCHDOG_GETUPDATES_MAX_AGE_SECONDS + 1)
        ctx = make_ctx()
        for _ in range(tb.WATCHDOG_MAX_FAILURES - 1):
            await tb.watchdog_check(ctx)
        self.assertEqual(self.exit_calls, [])
        with self.assertRaises(SystemExit):
            await tb.watchdog_check(ctx)
        self.assertEqual(self.exit_calls, [1])

    async def test_recovers_after_getupdates_becomes_fresh_again(self):
        tb._last_get_updates_at = time.monotonic() - (tb.WATCHDOG_GETUPDATES_MAX_AGE_SECONDS + 1)
        ctx = make_ctx()
        await tb.watchdog_check(ctx)
        self.assertEqual(ctx.application.bot_data["watchdog_failures"], 1)

        tb._last_get_updates_at = time.monotonic()
        await tb.watchdog_check(ctx)
        self.assertEqual(ctx.application.bot_data["watchdog_failures"], 0)
        self.assertEqual(self.exit_calls, [])


if __name__ == "__main__":
    unittest.main()
