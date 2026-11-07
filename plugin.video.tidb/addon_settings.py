# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Read the add-on's settings as the settings dialog last saved them.

Why this exists rather than plain `getSetting()`: Kodi reads an add-on's settings
from its user settings file **once** and caches them on the add-on object, and
`xbmcaddon.Addon(id)` hands back the add-on manager's cached CAddon — the same
object every time. So `getSetting()` keeps answering from whenever the add-on was
loaded, and a setting the user changes in the settings dialog stays invisible to
this service until Kodi restarts. (Kodi 21: `CAddon::GetSetting` calls
`LoadSettings(false, ...)`, which returns early once the settings are initialized,
and `Addon::Addon` wraps `CAddonMgr::GetAddon`.) That is why "I set the API key"
reported no key until a restart, and why enabling a feature appeared to do
nothing.

The dialog writes the values to `<profile>/settings.xml` when it closes, so that
file is the fresh source. Reading it costs a small XML parse, and the fallback
keeps the old behaviour for anything the file does not carry — including the case
where a future Kodi changes the file's shape.
"""
import os
import xml.etree.ElementTree as ElementTree
from typing import Dict

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
_ADDON_ID = ADDON.getAddonInfo('id')

#: Last read file, keyed by path + mtime so a poll loop does not re-parse it.
_cache: Dict[str, object] = {'path': '', 'mtime': None, 'values': {}}


def _settings_path() -> str:
    try:
        profile = xbmcvfs.translatePath(ADDON.getAddonInfo('profile') or '')
    except Exception:
        return ''
    if not profile:
        return ''
    return os.path.join(profile, 'settings.xml')


def _saved_values() -> Dict[str, str]:
    """The values in the user settings file, or {} when it cannot be read."""
    path = _settings_path()
    if not path:
        return {}
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {}
    if _cache['path'] == path and _cache['mtime'] == mtime:
        return _cache['values']  # type: ignore[return-value]

    try:
        root = ElementTree.parse(path).getroot()
    except Exception as e:
        xbmc.log('[TheIntroDB] Could not read {}: {}'.format(path, e), xbmc.LOGWARNING)
        return {}

    values: Dict[str, str] = {}
    for element in root.iter('setting'):
        key = element.get('id')
        if key:
            values[key] = element.text or ''
    if not values:
        xbmc.log('[TheIntroDB] No settings found in {}'.format(path), xbmc.LOGWARNING)
        return {}

    _cache['path'] = path
    _cache['mtime'] = mtime
    _cache['values'] = values
    return values


def setting(key: str, default: str = '') -> str:
    """A setting's saved value; falls back to the add-on's own (cached) answer."""
    value = _saved_values().get(key)
    if value is not None:
        return value
    try:
        return ADDON.getSetting(key) or default
    except Exception:
        return default


def setting_bool(key: str, default: bool = False) -> bool:
    """A boolean setting's saved value."""
    return str(setting(key, 'true' if default else 'false')).strip().lower() == 'true'
