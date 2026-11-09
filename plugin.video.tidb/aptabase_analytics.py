# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 TheIntroDB
#
import datetime
import json
import locale
import os
import platform
import queue
import random
import threading
import time
from typing import Optional, Dict, Any, List, Tuple

import xbmc
import xbmcaddon
import xbmcvfs

import addon_settings

ADDON = xbmcaddon.Addon()
_ADDON_ID = ADDON.getAddonInfo('id')
APTABASE_HOST = 'https://analytics.theintrodb.org'
APTABASE_APP_KEY = 'A-SH-5507621118'
SESSION_TIMEOUT_SECS = 3600.0
PERSIST_INTERVAL_SECS = 30.0


def _fresh_setting(key: str) -> str:
    return addon_settings.setting(key)


def _fresh_bool(key: str) -> bool:
    return addon_settings.setting_bool(key)


def _utc_iso() -> str:
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def _new_session_id() -> str:
    epoch_seconds = int(time.time())
    return '{}{:08d}'.format(epoch_seconds, random.randint(0, 99999999))


def _get_config() -> Tuple[bool, str, str]:
    enabled = _fresh_bool('anonymous_usage_reporting')
    host = APTABASE_HOST
    app_key = APTABASE_APP_KEY
    return enabled, host, app_key


def _state_file_path() -> str:
    try:
        profile = ADDON.getAddonInfo('profile') or ''
        profile = xbmcvfs.translatePath(profile)
        if profile:
            xbmcvfs.mkdirs(profile)
            return os.path.join(profile, 'aptabase_state.json')
    except Exception:
        return ''
    return ''


def _read_json(path: str) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        if not xbmcvfs.exists(path):
            return {}
        f = xbmcvfs.File(path)
        try:
            raw = f.read()
        finally:
            f.close()
        if not raw:
            return {}
        return json.loads(raw)
    except Exception:
        return {}


def _write_json(path: str, data: Dict[str, Any]) -> None:
    if not path:
        return
    try:
        raw = json.dumps(data, separators=(',', ':'))
        f = xbmcvfs.File(path, 'w')
        try:
            f.write(raw)
        finally:
            f.close()
    except Exception:
        return


class AptabaseReporter:
    def __init__(self) -> None:
        self._q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._stop = threading.Event()
        self._state_path = _state_file_path()
        self._state: Dict[str, Any] = _read_json(self._state_path)
        now = time.time()
        persisted_session_id = str(self._state.get('session_id') or '')
        persisted_last_touch = float(self._state.get('last_touch_ts') or 0.0)
        if persisted_session_id and persisted_last_touch and (now - persisted_last_touch) <= SESSION_TIMEOUT_SECS:
            self._session_id = persisted_session_id
            self._last_touch_ts = persisted_last_touch
        else:
            self._session_id = _new_session_id()
            self._last_touch_ts = 0.0
        self._last_persist_ts = 0.0
        self._thread = threading.Thread(target=self._worker, name='tidb-aptabase', daemon=True)
        self._thread.start()
        if _fresh_bool('debug_logging'):
            enabled, host, app_key = _get_config()
            safe_key = app_key[-6:] if app_key else ''
            xbmc.log('[TheIntroDB] Aptabase init enabled={} host={} key=*{} session=*{}'.format(enabled, host, safe_key, self._session_id[-6:]), xbmc.LOGINFO)

    def track_daily(self, event_name: str, props: Optional[Dict[str, Any]] = None) -> None:
        try:
            day = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        except Exception:
            day = ''
        if not day or not event_name:
            return
        key = 'daily_sent_{}'.format(event_name)
        if str(self._state.get(key) or '') == day:
            return
        self._state[key] = day
        self.track(event_name, props, force_persist=True)

    def _persist_state(self, now: float, force: bool = False) -> None:
        if not force and (now - self._last_persist_ts) < PERSIST_INTERVAL_SECS:
            return
        _write_json(self._state_path, self._state)
        self._last_persist_ts = now

    def track(self, event_name: str, props: Optional[Dict[str, Any]] = None, force_persist: bool = False) -> None:
        enabled, host, app_key = _get_config()
        if not enabled or not host or not app_key or not event_name:
            return
        now = time.time()
        if self._last_touch_ts and (now - self._last_touch_ts) > SESSION_TIMEOUT_SECS:
            self._session_id = _new_session_id()

        clean_props: Dict[str, Any] = {}
        if isinstance(props, dict):
            for k, v in props.items():
                if isinstance(v, (str, int, float)) or v is None:
                    clean_props[str(k)] = v
                else:
                    clean_props[str(k)] = str(v)

        self._last_touch_ts = now
        self._state['session_id'] = self._session_id
        self._state['last_touch_ts'] = self._last_touch_ts
        self._persist_state(now, force=force_persist)

        try:
            self._q.put_nowait({
                'eventName': event_name,
                'sessionId': self._session_id,
                'props': clean_props,
            })
        except Exception:
            return

    def flush(self, timeout: float = 2.0) -> None:
        deadline = time.time() + max(0.0, float(timeout))
        while time.time() < deadline:
            if self._q.empty():
                return
            time.sleep(0.05)

    def close(self, timeout: float = 2.0) -> None:
        self._stop.set()
        try:
            self._thread.join(timeout=max(0.0, float(timeout)))
        except Exception:
            pass
        try:
            now = time.time()
            self._state['session_id'] = self._session_id
            self._state['last_touch_ts'] = self._last_touch_ts
            self._persist_state(now, force=True)
        except Exception:
            pass

    def _system_props(self) -> Dict[str, Any]:
        try:
            loc = locale.getdefaultlocale()[0] or ''
        except Exception:
            loc = ''
        try:
            app_version = ADDON.getAddonInfo('version') or ''
        except Exception:
            app_version = ''
        is_debug = _fresh_bool('debug_logging') if _fresh_setting('debug_logging') else False
        return {
            'locale': loc,
            'osName': platform.system(),
            'osVersion': platform.release(),
            'deviceModel': platform.machine(),
            'isDebug': bool(is_debug),
            'appVersion': app_version,
            'sdkVersion': 'kodi-addon@1',
        }

    def _worker(self) -> None:
        buf: List[Dict[str, Any]] = []
        last_flush = time.time()
        flush_interval = 5.0
        max_batch = 25

        while not self._stop.is_set():
            got_item = None
            try:
                got_item = self._q.get(timeout=0.25)
                buf.append(got_item)
            except queue.Empty:
                pass
            except Exception:
                continue

            now = time.time()
            should_flush = (len(buf) >= max_batch) or (buf and (now - last_flush) >= flush_interval)
            if not should_flush:
                continue

            self._send_batch(buf[:max_batch])
            del buf[:max_batch]
            last_flush = now

        if buf:
            self._send_batch(buf)

    def _send_batch(self, items: List[Dict[str, Any]]) -> None:
        enabled, host, app_key = _get_config()
        if not enabled or not host or not app_key or not items:
            return

        payload = []
        sys_props = self._system_props()
        for item in items:
            payload.append({
                'timestamp': _utc_iso(),
                'sessionId': item.get('sessionId') or self._session_id,
                'eventName': item.get('eventName'),
                'systemProps': sys_props,
                'props': item.get('props') or {},
            })

        try:
            from urllib.request import Request, urlopen
            from urllib.error import HTTPError
        except ImportError:
            from urllib2 import Request, urlopen

        try:
            body = json.dumps(payload).encode('utf-8')
            req = Request('{}/api/v0/events'.format(host), data=body, method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('App-Key', app_key)
            resp = urlopen(req, timeout=5)
            try:
                resp.read()
            except Exception:
                pass
            if _fresh_bool('debug_logging'):
                xbmc.log('[TheIntroDB] Aptabase sent {} event(s)'.format(len(payload)), xbmc.LOGINFO)
        except HTTPError as e:
            if _fresh_bool('debug_logging'):
                try:
                    body_text = e.read().decode('utf-8', 'replace')
                except Exception:
                    body_text = ''
                xbmc.log('[TheIntroDB] Aptabase HTTP {} {}'.format(e.code, body_text[:400]), xbmc.LOGWARNING)
        except Exception as e:
            if _fresh_bool('debug_logging'):
                xbmc.log('[TheIntroDB] Aptabase send failed: {}'.format(e), xbmc.LOGWARNING)
