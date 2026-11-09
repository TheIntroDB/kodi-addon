# SPDX-License-Identifier: GPL-3.0-or-later
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
file is the fresh source. It is read and parsed on every call rather than cached:
it is about a kilobyte, reading and parsing it takes ~20 µs, and this add-on reads
a handful of settings per second — while *any* cache keyed on the file's timestamp
can miss a write that lands in the same tick (filesystems with one-second
granularity, or a writer that preserves the timestamp), which is the staleness
this module exists to remove.

The fallback keeps the old behaviour for anything the file does not carry — a
fresh install has no file, and a future Kodi may change its shape.
"""
import os
import xml.etree.ElementTree as ElementTree
from typing import Dict

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
_ADDON_ID = ADDON.getAddonInfo('id')


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
    if not path or not os.path.exists(path):
        return {}

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
