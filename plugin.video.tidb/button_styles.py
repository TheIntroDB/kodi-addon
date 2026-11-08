# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Which pill style the overlay windows are drawn with.

A style is a folder under resources/skins/ that Kodi loads as the overlay window's own
skin: WindowXMLDialog(xml, addon_path, skin, res) resolves, in order, the active Kodi
skin, then resources/skins/<active skin id>/<res>/, and finally
resources/skins/<skin argument>/<res>/ — the third argument is used verbatim as a folder
name, and that folder is registered as a skin path so the relative texture paths inside
it resolve (xbmc/interfaces/legacy/WindowXML.cpp). The style setting picks the folder.

Styles are read through addon_settings, so a style chosen in the settings dialog applies
to the next prompt rather than after a Kodi restart (see addon_settings for why
getSetting() cannot see the change).
"""
import os
from typing import Tuple

import xbmcvfs

import addon_settings

# Keep in step with resources/skins/<style>/ and with the button_style setting in
# resources/settings.xml; tests/test_button_styles.py checks all three.
STYLES: Tuple[str, ...] = ('default', 'glass')
DEFAULT_STYLE = 'default'
SETTING_ID = 'button_style'


def _styles_root(addon_path: str) -> str:
    return os.path.join(addon_path, 'resources', 'skins')


def _style_path(addon_path: str, style: str, res: str) -> str:
    return os.path.join(_styles_root(addon_path), style, res)


def _exists(path: str) -> bool:
    try:
        if xbmcvfs.exists(path):
            return True
    except Exception:
        pass
    return os.path.isdir(path)


def available(addon_path: str, res: str) -> Tuple[str, ...]:
    """The styles whose folder for this resolution is actually installed."""
    return tuple(style for style in STYLES
                 if _exists(_style_path(addon_path, style, res)))


def resolve(addon_path: str, res: str) -> str:
    """The configured style, or the default when that style cannot be used.

    Falling back rather than failing is the point: an unknown — or half-installed —
    style makes WindowXML raise WindowException("XML File for Window is missing") and
    the prompt never appears, which is worse than the wrong look.
    """
    try:
        chosen = addon_settings.setting(SETTING_ID).strip().lower()
    except Exception:
        chosen = ''
    if chosen in STYLES and _exists(_style_path(addon_path, chosen, res)):
        return chosen
    return DEFAULT_STYLE
