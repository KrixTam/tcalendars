import unittest
import pandas as pd
import os
import json
import time
import tempfile
import importlib
import sys
import runpy
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
from os import path
from moment import moment
from tcalendars.tools.get_se_calendar import get_calendar_filename, get_calendar
from tcalendars.db import DatabaseManager

CWD = path.abspath(path.dirname(__file__))


class TestTools(unittest.TestCase):
    def test_get_se_calendars_01(self):
        get_calendar('2005-02-01', '2005-03-01')
        db = DatabaseManager()
        a = db.read_dataframe('se_calendar')
        b = pd.read_csv(path.join(CWD, 'calendar.csv'))
        # 确保类型一致以便比较
        a['zrxh'] = a['zrxh'].astype(int)
        a['jybz'] = a['jybz'].astype(int)
        a['jyrq'] = a['jyrq'].astype(str)
        b['zrxh'] = b['zrxh'].astype(int)
        b['jybz'] = b['jybz'].astype(int)
        b['jyrq'] = b['jyrq'].astype(str)
        self.assertTrue(a.equals(b))

    def test_get_se_calendars_append_dedup(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rows_1 = [
                {"zrxh": 3, "jybz": 1, "jyrq": "2005-02-01"},
            ]
            rows_2 = [
                {"zrxh": 3, "jybz": 1, "jyrq": "2005-02-01"},
                {"zrxh": 4, "jybz": 1, "jyrq": "2005-02-02"},
            ]
            with patch("tcalendars.tools.get_se_calendar.get_dates_by_month", side_effect=[rows_1, rows_2]):
                get_calendar(start_date="2005-02-01", end_date="2005-02-01", dir=tmp_dir)
                get_calendar(append=True, start_date="2005-02-01", end_date="2005-02-01", dir=tmp_dir)

            db = DatabaseManager(tmp_dir)
            df = db.read_dataframe('se_calendar')
            self.assertEqual(df["jyrq"].tolist(), ["2005-02-01", "2005-02-02"])

    def test_get_se_calendars_append_empty_file_has_header(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = get_calendar_filename(tmp_dir)
            # DatabaseManager(tmp_dir) 会自动创建表
            db = DatabaseManager(tmp_dir)
            # 确保表为空
            db.execute('DELETE FROM se_calendar')
            
            rows = [{"zrxh": 3, "jybz": 1, "jyrq": "2005-02-01"}]
            with patch("tcalendars.tools.get_se_calendar.get_dates_by_month", return_value=rows):
                get_calendar(append=True, start_date="2005-02-01", end_date="2005-02-01", dir=tmp_dir)

            db = DatabaseManager(tmp_dir)
            with closing(db.get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(se_calendar)")
                columns = [info[1] for info in cursor.fetchall()]
            self.assertEqual(columns, ["zrxh", "jybz", "jyrq"])

    def test_get_se_calendars_append_dedup_in_while_loop(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            rows_feb = [{"zrxh": 3, "jybz": 1, "jyrq": "2005-02-01"}]
            rows_mar = [
                {"zrxh": 3, "jybz": 1, "jyrq": "2005-02-01"},
                {"zrxh": 4, "jybz": 1, "jyrq": "2005-03-01"},
            ]
            with patch("tcalendars.tools.get_se_calendar.get_dates_by_month", side_effect=[rows_feb, rows_mar]):
                get_calendar(append=True, start_date="2005-02-01", end_date="2005-03-01", dir=tmp_dir)

            db = DatabaseManager(tmp_dir)
            df = db.read_dataframe('se_calendar')
            self.assertEqual(df["jyrq"].tolist(), ["2005-02-01", "2005-03-01"])

    def test_get_se_calendars_02(self):
        now = moment().format('YYYY-10-01')
        get_calendar(now)
        db = DatabaseManager()
        a = db.read_dataframe('se_calendar')
        get_calendar(now, moment().format('YYYY-12-02'))
        b = db.read_dataframe('se_calendar')
        self.assertTrue(a.equals(b))

    def test_get_calendar_filename_01(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename = get_calendar_filename(tmp_dir)
            self.assertEqual(filename, path.join(tmp_dir, 'cache', 'data.dat'))

    def test_yfinance_cache_load_filters_old(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            yq = importlib.import_module("tcalendars.tools.yfinance_query")
            yq._CACHE_FILE = Path(tmp_dir) / "cache" / ".yfinance_cache"
            yq._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            now = int(time.time())
            cache = {
                "https://example.com/new": {"ts": now - 59 * 24 * 60 * 60, "data": {"k": "v"}},
                "https://example.com/old": {"ts": now - 61 * 24 * 60 * 60, "data": {"k": "v2"}},
            }
            yq._CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            yq._API_CACHE.clear()
            yq._API_CACHE_TS.clear()
            yq._load_api_cache_from_disk()

            self.assertIn("https://example.com/new", yq._API_CACHE)
            self.assertNotIn("https://example.com/old", yq._API_CACHE)

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
            yq = importlib.import_module("tcalendars.tools.yfinance_query")
            yq._CACHE_FILE = Path(tmp_dir) / "cache" / ".yfinance_cache"
            yq._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            yq._API_CACHE.clear()
            yq._API_CACHE_TS.clear()

            yq.sync_playwright = lambda: _DummyPlaywrightManager()

            persist_calls = {"count": 0}

            def _persist_spy():
                persist_calls["count"] += 1

            with patch.object(yq, "_persist_api_cache_to_disk", new=_persist_spy):
                a = yq.search_yahoo_finance(query="AAPL", region="US", lang="zh_HK", quotes_count=1)
                b = yq.search_yahoo_finance(query="AAPL", region="US", lang="zh_HK", quotes_count=1)

            self.assertEqual(a, {"count": 1, "quotes": [{"symbol": "AAPL"}]})
            self.assertEqual(b, {"count": 1, "quotes": [{"symbol": "AAPL"}]})
            self.assertEqual(persist_calls["count"], 1)

    def test_yfinance_cache_load_invalid_json_returns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            yq = importlib.import_module("tcalendars.tools.yfinance_query")
            yq._CACHE_FILE = Path(tmp_dir) / "cache" / ".yfinance_cache"
            yq._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            yq._CACHE_FILE.write_text("{invalid json", encoding="utf-8")
            yq._API_CACHE.clear()
            yq._API_CACHE_TS.clear()
            yq._load_api_cache_from_disk()
            self.assertEqual(yq._API_CACHE, {})

    def test_yfinance_cache_load_non_dict_root_returns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            yq = importlib.import_module("tcalendars.tools.yfinance_query")
            yq._CACHE_FILE = Path(tmp_dir) / "cache" / ".yfinance_cache"
            yq._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            yq._CACHE_FILE.write_text(json.dumps([1, 2, 3], ensure_ascii=False), encoding="utf-8")
            yq._API_CACHE.clear()
            yq._API_CACHE_TS.clear()
            yq._load_api_cache_from_disk()
            self.assertEqual(yq._API_CACHE, {})

    def test_yfinance_cache_load_skips_bad_entries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            yq = importlib.import_module("tcalendars.tools.yfinance_query")
            yq._CACHE_FILE = Path(tmp_dir) / "cache" / ".yfinance_cache"
            yq._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            yq._CACHE_FILE.write_text("{}", encoding="utf-8")

            with patch.object(yq.json, "loads", return_value={1: {"ts": 0, "data": {}}, "u": "x"}):
                yq._API_CACHE.clear()
                yq._API_CACHE_TS.clear()
                yq._load_api_cache_from_disk()

            self.assertEqual(yq._API_CACHE, {})

    def test_yfinance_cache_load_legacy_shape_kept(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            yq = importlib.import_module("tcalendars.tools.yfinance_query")
            yq._CACHE_FILE = Path(tmp_dir) / "cache" / ".yfinance_cache"
            yq._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            now = int(time.time())
            yq._CACHE_FILE.write_text(json.dumps({"https://example.com/legacy": {"a": 1}}, ensure_ascii=False), encoding="utf-8")
            yq._API_CACHE.clear()
            yq._API_CACHE_TS.clear()
            yq._load_api_cache_from_disk()

            self.assertEqual(yq._API_CACHE["https://example.com/legacy"], {"a": 1})
            self.assertIn("https://example.com/legacy", yq._API_CACHE_TS)
            self.assertTrue(now - yq._API_CACHE_TS["https://example.com/legacy"] <= 5)

    def test_yfinance_cache_persist_writes_schema_and_sets_ts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            yq = importlib.import_module("tcalendars.tools.yfinance_query")
            yq._CACHE_FILE = Path(tmp_dir) / "cache" / ".yfinance_cache"
            yq._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            yq._API_CACHE.clear()
            yq._API_CACHE_TS.clear()
            yq._API_CACHE["https://example.com/a"] = {"x": 1}

            with patch.object(yq.time, "time", return_value=1234567890.0):
                yq._persist_api_cache_to_disk()

            data = json.loads(yq._CACHE_FILE.read_text(encoding="utf-8"))
            self.assertIn("https://example.com/a", data)
            self.assertEqual(data["https://example.com/a"]["data"], {"x": 1})
            self.assertEqual(data["https://example.com/a"]["ts"], 1234567890)
            self.assertEqual(yq._API_CACHE_TS["https://example.com/a"], 1234567890)

    def test_yfinance_cache_persist_replace_error_cleans_tmp(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            yq = importlib.import_module("tcalendars.tools.yfinance_query")
            yq._CACHE_FILE = Path(tmp_dir) / "cache" / ".yfinance_cache"
            yq._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            yq._API_CACHE.clear()
            yq._API_CACHE_TS.clear()
            yq._API_CACHE["https://example.com/a"] = {"x": 1}
            yq._API_CACHE_TS["https://example.com/a"] = 1

            def _raise_replace(_src, _dst):
                raise RuntimeError("fail")

            tmp_path = yq._CACHE_FILE.with_suffix(yq._CACHE_FILE.suffix + ".tmp")
            with patch.object(yq.os, "replace", side_effect=_raise_replace):
                yq._persist_api_cache_to_disk()

            self.assertFalse(tmp_path.exists())

    def test_yfinance_search_handles_response_not_ok(self):
        class _DummyResponse:
            ok = False
            status = 500

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
                if page_ref["page"] is None:
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
                    with patch("pathlib.Path.is_file", return_value=False):
                        with patch("pathlib.Path.write_text", return_value=0):
                            with patch("os.replace", return_value=None):
                                runpy.run_module("tcalendars.tools.yfinance_query", run_name="__main__")

                self.assertIsNotNone(page_ref["page"])
            finally:
                os.chdir(prev_cwd)


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
