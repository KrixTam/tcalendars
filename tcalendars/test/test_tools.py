import unittest
import pandas as pd
import os
import json
import time
import tempfile
import importlib
import sys
import runpy
from unittest.mock import patch
from os import path
from moment import moment
from tcalendars.tools.get_se_calendar import get_calendar_filename, get_calendar

CWD = path.abspath(path.dirname(__file__))


class TestTools(unittest.TestCase):
    def test_get_se_calendars_01(self):
        get_calendar('2005-02-01', '2005-03-01')
        a = pd.read_csv(get_calendar_filename())
        b = pd.read_csv(path.join(CWD, 'calendar.csv'))
        self.assertTrue(a.equals(b))

    def test_get_se_calendars_02(self):
        now = moment().format('YYYY-10-01')
        get_calendar(now)
        a = pd.read_csv(get_calendar_filename())
        get_calendar(now, moment().format('YYYY-12-02'))
        b = pd.read_csv(get_calendar_filename())
        self.assertTrue(a.equals(b))

    def test_get_calendar_filename_01(self):
        filename = get_calendar_filename('.')
        self.assertEqual(filename, './se_calendar.csv')

    def test_yfinance_cache_load_filters_old(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                now = int(time.time())
                cache = {
                    "https://example.com/new": {"ts": now - 59 * 24 * 60 * 60, "data": {"k": "v"}},
                    "https://example.com/old": {"ts": now - 61 * 24 * 60 * 60, "data": {"k": "v2"}},
                }
                with open(".yfinance_cache", "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False)

                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")

                self.assertIn("https://example.com/new", yq._API_CACHE)
                self.assertNotIn("https://example.com/old", yq._API_CACHE)
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_cache_persist_only_on_new_entry(self):
        class _DummyResponse:
            ok = True
            status = 200

            def json(self):
                return {"count": 1, "quotes": [{"symbol": "AAPL"}]}

        class _DummyPage:
            def goto(self, *_args, **_kwargs):
                return _DummyResponse()

        class _DummyContext:
            def new_page(self):
                return _DummyPage()

        class _DummyBrowser:
            def new_context(self, **_kwargs):
                return _DummyContext()

            def close(self):
                pass

        class _DummyChromium:
            def launch(self, headless=True):
                _ = headless
                return _DummyBrowser()

        class _DummyPlaywright:
            chromium = _DummyChromium()

        class _DummyPlaywrightManager:
            def __enter__(self):
                return _DummyPlaywright()

            def __exit__(self, exc_type, exc, tb):
                return False

        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")

                yq.sync_playwright = lambda: _DummyPlaywrightManager()

                persist_calls = {"count": 0}

                def _persist_spy():
                    persist_calls["count"] += 1

                yq._persist_api_cache_to_disk = _persist_spy

                a = yq.search_yahoo_finance(query="AAPL", region="US", lang="zh_HK", quotes_count=1)
                b = yq.search_yahoo_finance(query="AAPL", region="US", lang="zh_HK", quotes_count=1)

                self.assertEqual(a, {"count": 1, "quotes": [{"symbol": "AAPL"}]})
                self.assertEqual(b, {"count": 1, "quotes": [{"symbol": "AAPL"}]})
                self.assertEqual(persist_calls["count"], 1)
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_cache_load_invalid_json_returns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                with open(".yfinance_cache", "w", encoding="utf-8") as f:
                    f.write("{invalid json")

                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")
                self.assertEqual(yq._API_CACHE, {})
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_cache_load_non_dict_root_returns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                with open(".yfinance_cache", "w", encoding="utf-8") as f:
                    json.dump([1, 2, 3], f, ensure_ascii=False)

                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")
                self.assertEqual(yq._API_CACHE, {})
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_cache_load_skips_bad_entries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                with open(".yfinance_cache", "w", encoding="utf-8") as f:
                    f.write("{}")

                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")

                with patch.object(yq.json, "loads", return_value={1: {"ts": 0, "data": {}}, "u": "x"}):
                    yq._API_CACHE.clear()
                    yq._API_CACHE_TS.clear()
                    yq._load_api_cache_from_disk()

                self.assertEqual(yq._API_CACHE, {})
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_cache_load_legacy_shape_kept(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                now = int(time.time())
                with open(".yfinance_cache", "w", encoding="utf-8") as f:
                    json.dump({"https://example.com/legacy": {"a": 1}}, f, ensure_ascii=False)

                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")

                self.assertEqual(yq._API_CACHE["https://example.com/legacy"], {"a": 1})
                self.assertIn("https://example.com/legacy", yq._API_CACHE_TS)
                self.assertTrue(now - yq._API_CACHE_TS["https://example.com/legacy"] <= 5)
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_cache_persist_writes_schema_and_sets_ts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")

                yq._API_CACHE.clear()
                yq._API_CACHE_TS.clear()
                yq._API_CACHE["https://example.com/a"] = {"x": 1}

                with patch.object(yq.time, "time", return_value=1234567890.0):
                    yq._persist_api_cache_to_disk()

                with open(".yfinance_cache", "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.assertIn("https://example.com/a", data)
                self.assertEqual(data["https://example.com/a"]["data"], {"x": 1})
                self.assertEqual(data["https://example.com/a"]["ts"], 1234567890)
                self.assertEqual(yq._API_CACHE_TS["https://example.com/a"], 1234567890)
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_cache_persist_replace_error_cleans_tmp(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")

                yq._API_CACHE.clear()
                yq._API_CACHE_TS.clear()
                yq._API_CACHE["https://example.com/a"] = {"x": 1}
                yq._API_CACHE_TS["https://example.com/a"] = 1

                def _raise_replace(_src, _dst):
                    raise RuntimeError("fail")

                with patch.object(yq.os, "replace", side_effect=_raise_replace):
                    yq._persist_api_cache_to_disk()

                self.assertFalse(os.path.exists(".yfinance_cache.tmp"))
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_search_handles_response_not_ok(self):
        class _DummyResponse:
            ok = False
            status = 500

            def json(self):
                raise RuntimeError("unexpected")

        class _DummyPage:
            def goto(self, *_args, **_kwargs):
                return _DummyResponse()

        class _DummyContext:
            def new_page(self):
                return _DummyPage()

        class _DummyBrowser:
            def new_context(self, **_kwargs):
                return _DummyContext()

            def close(self):
                pass

        class _DummyChromium:
            def launch(self, headless=True):
                _ = headless
                return _DummyBrowser()

        class _DummyPlaywright:
            chromium = _DummyChromium()

        class _DummyPlaywrightManager:
            def __enter__(self):
                return _DummyPlaywright()

            def __exit__(self, exc_type, exc, tb):
                return False

        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")
                yq.sync_playwright = lambda: _DummyPlaywrightManager()

                result = yq.search_yahoo_finance(query="AAPL", region="US", lang="zh_HK", quotes_count=1)
                self.assertIsNone(result)
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_search_handles_json_parse_error(self):
        class _DummyResponse:
            ok = True
            status = 200

            def json(self):
                raise ValueError("bad json")

        class _DummyPage:
            def goto(self, *_args, **_kwargs):
                return _DummyResponse()

        class _DummyContext:
            def new_page(self):
                return _DummyPage()

        class _DummyBrowser:
            def new_context(self, **_kwargs):
                return _DummyContext()

            def close(self):
                pass

        class _DummyChromium:
            def launch(self, headless=True):
                _ = headless
                return _DummyBrowser()

        class _DummyPlaywright:
            chromium = _DummyChromium()

        class _DummyPlaywrightManager:
            def __enter__(self):
                return _DummyPlaywright()

            def __exit__(self, exc_type, exc, tb):
                return False

        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")
                yq.sync_playwright = lambda: _DummyPlaywrightManager()

                result = yq.search_yahoo_finance(query="AAPL", region="US", lang="zh_HK", quotes_count=1)
                self.assertIsNone(result)
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_search_handles_playwright_exception(self):
        class _DummyBrowser:
            def __init__(self):
                self.closed = False

            def new_context(self, **_kwargs):
                raise RuntimeError("boom")

            def close(self):
                self.closed = True

        browser_ref = {"browser": None}

        class _DummyChromium:
            def launch(self, headless=True):
                _ = headless
                browser_ref["browser"] = _DummyBrowser()
                return browser_ref["browser"]

        class _DummyPlaywright:
            chromium = _DummyChromium()

        class _DummyPlaywrightManager:
            def __enter__(self):
                return _DummyPlaywright()

            def __exit__(self, exc_type, exc, tb):
                return False

        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                yq = importlib.import_module("tcalendars.tools.yfinance_query")
                yq.sync_playwright = lambda: _DummyPlaywrightManager()

                result = yq.search_yahoo_finance(query="AAPL", region="US", lang="zh_HK", quotes_count=1)
                self.assertIsNone(result)
                self.assertTrue(browser_ref["browser"].closed)
            finally:
                os.chdir(prev_cwd)

    def test_yfinance_query_main_block_runs(self):
        class _DummyResponse:
            ok = True
            status = 200

            def __init__(self, payload):
                self._payload = payload

            def json(self):
                return self._payload

        class _DummyPage:
            def __init__(self):
                self.calls = 0

            def goto(self, *_args, **_kwargs):
                self.calls += 1
                if self.calls == 1:
                    return _DummyResponse({"count": 1, "quotes": [{"symbol": "PONY", "shortname": "Pony AI"}]})
                return _DummyResponse({"count": 1, "quotes": [{"symbol": "AAPL", "shortname": "Apple"}]})

        page_ref = {"page": None}

        class _DummyContext:
            def new_page(self):
                page_ref["page"] = _DummyPage()
                return page_ref["page"]

        class _DummyBrowser:
            def new_context(self, **_kwargs):
                return _DummyContext()

            def close(self):
                pass

        class _DummyChromium:
            def launch(self, headless=True):
                _ = headless
                return _DummyBrowser()

        class _DummyPlaywright:
            chromium = _DummyChromium()

        class _DummyPlaywrightManager:
            def __enter__(self):
                return _DummyPlaywright()

            def __exit__(self, exc_type, exc, tb):
                return False

        with tempfile.TemporaryDirectory() as tmp_dir:
            prev_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                sys.modules.pop("tcalendars.tools.yfinance_query", None)
                with patch("playwright.sync_api.sync_playwright", new=lambda: _DummyPlaywrightManager()):
                    runpy.run_module("tcalendars.tools.yfinance_query", run_name="__main__")

                self.assertIsNotNone(page_ref["page"])
            finally:
                os.chdir(prev_cwd)


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
