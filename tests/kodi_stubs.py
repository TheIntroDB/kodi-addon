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
import sys
import types

ADDON_PATH = '/tmp/tidb-addon'
PROFILE_PATH = '/tmp/tidb-addon-profile'
#: Settings the add-on reads, keyed by setting id. Tests set entries directly.
SETTINGS = {}
#: Builtins the add-on executed, oldest first (Notification, etc.).
EXECUTED_BUILTINS = []
#: JSON-RPC calls made through xbmc.executeJSONRPC, oldest first.
JSONRPC_CALLS = []


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
    def __init__(self, control_id):
        self.control_id = control_id
        self.visible = None
        self.label = None
        self.image = None
        self.enabled = None

    def setVisible(self, visible):
        self.visible = visible

    def isVisible(self):
        return bool(self.visible)

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
        self.window_closed = False

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
