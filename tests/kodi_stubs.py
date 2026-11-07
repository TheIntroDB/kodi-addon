# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Kodi module stubs for the unit tests.

Kodi's xbmc* modules do not exist off-device, so the add-on modules are imported
against these. They live in one place, with one SETTINGS dict, because the suite
must pass whatever order its test modules are loaded in: a module that installed
its own stubs and its own settings would answer another module's add-on
instances, and the tests that rely on a configured value would silently see none.

Importing this module installs the stubs into sys.modules, so it must be
imported before any add-on module.
"""
import os
import sys
import time
import types
import xml.etree.ElementTree as ElementTree

ADDON_PATH = '/tmp/tidb-addon'
PROFILE_PATH = '/tmp/tidb-addon-profile'
#: The user settings file the settings dialog writes, and the add-on reads.
SETTINGS_FILE = os.path.join(PROFILE_PATH, 'settings.xml')
#: Settings the add-on reads through getSetting(), keyed by setting id. These stand
#: for what Kodi cached when the add-on loaded: writing here is *not* how a user
#: changes a setting, and the add-on must not rely on it for a fresh value.
SETTINGS = {}
#: Builtins the add-on executed, oldest first (Notification, etc.).
EXECUTED_BUILTINS = []
#: JSON-RPC calls made through xbmc.executeJSONRPC, oldest first.
JSONRPC_CALLS = []

_write_clock = [0.0]


def read_settings():
    """The values in the user settings file, as a dict."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    root = ElementTree.parse(SETTINGS_FILE).getroot()
    return {element.get('id'): (element.text or '') for element in root.iter('setting')}


def write_settings(values, keep_existing=False):
    """Write the user settings file, the way the settings dialog does on close.

    Each write bumps the mtime past the previous one, so a reader that caches by
    mtime cannot miss a change made in the same second.
    """
    if keep_existing:
        merged = read_settings()
        merged.update(values)
        values = merged
    os.makedirs(PROFILE_PATH, exist_ok=True)
    body = '\n'.join('    <setting id="{}">{}</setting>'.format(key, value)
                     for key, value in sorted(values.items()))
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as handle:
        handle.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                     '<settings version="2">\n{}\n</settings>\n'.format(body))
    _write_clock[0] += 1.0
    stamp = time.time() + _write_clock[0]
    os.utime(SETTINGS_FILE, (stamp, stamp))
    return SETTINGS_FILE


def remove_settings():
    """Delete the user settings file, as a fresh install has none."""
    try:
        os.remove(SETTINGS_FILE)
    except OSError:
        pass


class Addon(object):
    def __init__(self, *args, **kwargs):
        pass

    def getAddonInfo(self, key):
        info = {
            'id': 'plugin.video.tidb',
            'name': 'TheIntroDB Kodi Addon',
            'path': ADDON_PATH,
            'profile': PROFILE_PATH,
            'version': '2.0.0',
        }
        return info.get(key, '')

    def getSetting(self, key):
        return SETTINGS.get(key, '')

    def setSetting(self, key, value):
        SETTINGS[key] = value

    def getLocalizedString(self, string_id):
        return 'string-{}'.format(string_id)


class Monitor(object):
    def abortRequested(self):
        return False

    def waitForAbort(self, timeout=None):
        return False


class Player(object):
    def __init__(self, *args, **kwargs):
        self._time = 0.0
        self._playing = False

    def isPlaying(self):
        return self._playing

    def isPlayingVideo(self):
        return self._playing

    def getTime(self):
        return self._time

    def getTotalTime(self):
        return 0.0

    def seekTime(self, target):
        self._time = target

    def getPlayingFile(self):
        return ''

    def getVideoInfoTag(self):
        raise RuntimeError('no video info tag in tests')


class Action(object):
    def __init__(self, action_id):
        self._id = action_id

    def getId(self):
        return self._id


class Control(object):
    """A control as Kodi drives it.

    Kodi's `Control.setVisible` only moves the force-hidden flag (CGUIControl::SetVisible
    is called from Python with setVisState false), so it can hide a control but never
    show one whose skin `<visible>` condition is false. Nothing here should be trusted
    to make a condition-hidden control appear — the report pill is driven by a window
    property for exactly that reason.
    """

    def __init__(self, control_id):
        self.control_id = control_id
        self.label = None
        self.image = None
        self.enabled = None
        self.force_hidden = False
        self.set_visible_calls = []

    def setVisible(self, visible):
        self.set_visible_calls.append(visible)
        self.force_hidden = not visible

    def setLabel(self, label):
        self.label = label

    def setImage(self, image):
        self.image = image

    def setEnabled(self, enabled):
        self.enabled = enabled


class ControlButton(Control):
    pass


class ControlImage(Control):
    pass


class WindowXMLDialog(object):
    """The window the add-on's overlays subclass, with its controls recorded."""

    BUTTON_IDS = (3001, 3002)
    IMAGE_IDS = (3003, 3004, 3005, 3006)

    def __new__(cls, *args, **kwargs):
        return super(WindowXMLDialog, cls).__new__(cls)

    def __init__(self, *args, **kwargs):
        self._controls = {}
        self._focus_id = None
        self._properties = {}
        self.window_closed = False

    def setProperty(self, key, value):
        """Kodi's CGUIWindow::SetProperty; an empty value clears the property."""
        if value:
            self._properties[str(key)] = str(value)
        else:
            self._properties.pop(str(key), None)

    def getProperty(self, key):
        return self._properties.get(str(key), '')

    def getControl(self, control_id):
        if control_id not in self._controls:
            if control_id in self.BUTTON_IDS:
                control_class = ControlButton
            elif control_id in self.IMAGE_IDS:
                control_class = ControlImage
            else:
                control_class = Control
            self._controls[control_id] = control_class(control_id)
        return self._controls[control_id]

    def setFocusId(self, control_id):
        self._focus_id = control_id

    def getFocusId(self):
        return self._focus_id

    def close(self):
        self.window_closed = True

    def doModal(self):
        pass


class Dialog(object):
    def ok(self, *args, **kwargs):
        return True

    def yesno(self, *args, **kwargs):
        return True

    def notification(self, *args, **kwargs):
        return True


class ListItem(object):
    def __init__(self, *args, **kwargs):
        pass


def _install():
    xbmc = sys.modules.get('xbmc') or types.ModuleType('xbmc')
    xbmc.LOGDEBUG = 0
    xbmc.LOGINFO = 1
    xbmc.LOGWARNING = 2
    xbmc.LOGERROR = 3
    xbmc.LOGFATAL = 4
    xbmc.LOGNONE = 5
    xbmc.log = lambda *args, **kwargs: None
    xbmc.Monitor = Monitor
    xbmc.Player = Player
    xbmc.getScreenHeight = lambda: 1080
    xbmc.getScreenWidth = lambda: 1920
    xbmc.getCondVisibility = lambda condition: False
    xbmc.getInfoLabel = lambda label: ''
    xbmc.executebuiltin = lambda builtin, *args, **kwargs: EXECUTED_BUILTINS.append(builtin)

    def execute_jsonrpc(payload, *args, **kwargs):
        JSONRPC_CALLS.append(payload)
        return '{"jsonrpc":"2.0","result":{},"id":1}'

    xbmc.executeJSONRPC = execute_jsonrpc
    sys.modules['xbmc'] = xbmc

    xbmcaddon = sys.modules.get('xbmcaddon') or types.ModuleType('xbmcaddon')
    xbmcaddon.Addon = Addon
    sys.modules['xbmcaddon'] = xbmcaddon

    xbmcgui = sys.modules.get('xbmcgui') or types.ModuleType('xbmcgui')
    xbmcgui.WindowXMLDialog = WindowXMLDialog
    xbmcgui.Control = Control
    xbmcgui.ControlButton = ControlButton
    xbmcgui.ControlImage = ControlImage
    xbmcgui.Action = Action
    xbmcgui.Dialog = Dialog
    xbmcgui.ListItem = ListItem
    sys.modules['xbmcgui'] = xbmcgui

    xbmcvfs = sys.modules.get('xbmcvfs') or types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda path: path
    xbmcvfs.exists = lambda path: False
    xbmcvfs.mkdirs = lambda path: None
    sys.modules['xbmcvfs'] = xbmcvfs


_install()
