# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
# submit_overlay.py — overlay for marking intro start/end timestamps during playback
# Reuses the same overlay.xml skin pill as the skip button.
import threading
import time
import xbmc
import xbmcgui
import xbmcaddon
from typing import Optional

import button_styles

ADDON = xbmcaddon.Addon()
ADDON_PATH: str = ADDON.getAddonInfo('path')


def _detect_res() -> str:
    try:
        height = xbmc.getScreenHeight()
        return '1080i' if height >= 1080 else '720p'
    except Exception:
        return '1080i'


_OVERLAY_RES = _detect_res()

# String IDs
STR_MARK_START = 32020
STR_MARK_END = 32021
STR_SUBMIT_SUCCESS = 32022
STR_SUBMIT_FAILED = 32023

OVERLAY_WINDOW_ID = 14000

ACTION_SELECT = 7
ACTION_PREVIOUS_MENU = 10
ACTION_BACK = 92
BUTTON_ID = 3001
# The report pill's button, which belongs to the skip prompt: this overlay shares
# overlay.xml with it, so it is hidden here rather than drawn.
FLAG_BUTTON_ID = 3002

_DISPLAY_DURATION = 8.0  # longer than skip since user is paused/deciding
_POLL_INTERVAL = 0.5


class SubmitMarkOverlay(xbmcgui.WindowXMLDialog):
    """Single-button overlay that says 'Mark Intro Start' or 'Mark Intro End'."""

    def __new__(cls, xml_file: str, addon_path: str, skin: str, res: str,
                label_text: str = '', player: Optional[xbmc.Player] = None,
                monitor: Optional[xbmc.Monitor] = None) -> 'SubmitMarkOverlay':
        return super(SubmitMarkOverlay, cls).__new__(cls, xml_file, addon_path, skin, res)  # type: ignore[call-arg]

    def __init__(self, xml_file: str, addon_path: str, skin: str, res: str,
                 label_text: str = '', player: Optional[xbmc.Player] = None,
                 monitor: Optional[xbmc.Monitor] = None) -> None:
        super(SubmitMarkOverlay, self).__init__(xml_file, addon_path, skin, res)
        self._button_pressed: bool = False
        self._label_text: str = label_text
        self._player: Optional[xbmc.Player] = player
        self._monitor: Optional[xbmc.Monitor] = monitor
        self._poll_thread: Optional[threading.Thread] = None
        self._closed: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._display_deadline: Optional[float] = None

    @property
    def button_pressed(self) -> bool:
        return self._button_pressed

    def onInit(self) -> None:
        mon = self._monitor if self._monitor is not None else xbmc.Monitor()
        if mon.abortRequested():
            self._dismiss_main_thread()
            return

        # The report pill belongs to the skip prompt, which shares this XML.
        try:
            self.getControl(FLAG_BUTTON_ID).setVisible(False)
        except Exception:
            pass

        # Set button label
        try:
            button_control = self.getControl(BUTTON_ID)
            if isinstance(button_control, xbmcgui.ControlButton):
                button_control.setLabel(self._label_text)
        except Exception as e:
            xbmc.log('[TheIntroDB] Submit overlay set label: {}'.format(e), xbmc.LOGWARNING)

        try:
            self.setFocusId(BUTTON_ID)
        except Exception:
            pass

        self._display_deadline = time.time() + _DISPLAY_DURATION
        self._poll_thread = threading.Thread(target=self._poll_loop)
        self._poll_thread.daemon = True
        self._poll_thread.start()

    def onClick(self, controlId: int) -> None:
        if controlId == BUTTON_ID:
            self._do_press()

    def onAction(self, action: xbmcgui.Action) -> None:
        aid = action.getId()
        if aid == ACTION_SELECT:
            try:
                if self.getFocusId() == BUTTON_ID:
                    self._do_press()
            except Exception:
                pass
            return
        if aid in (ACTION_PREVIOUS_MENU, ACTION_BACK):
            self._dismiss_main_thread()

    def _do_press(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._button_pressed = True
        self._stop_poll_thread()
        self._dismiss_main_thread()

    def _poll_loop(self) -> None:
        mon = self._monitor if self._monitor is not None else xbmc.Monitor()
        while True:
            with self._lock:
                if self._closed:
                    return
            if mon.abortRequested():
                self._close_from_bg_thread()
                return
            if mon.waitForAbort(_POLL_INTERVAL):
                self._close_from_bg_thread()
                return
            try:
                if self._display_deadline is not None and time.time() >= self._display_deadline:
                    self._close_from_bg_thread()
                    return
                # Close if playback resumes (user unpaused without pressing)
                pl = self._player
                if pl and pl.isPlaying():
                    try:
                        speed = xbmc.getCondVisibility('Player.Paused')
                        if not speed:
                            # Player is no longer paused — dismiss
                            self._close_from_bg_thread()
                            return
                    except Exception:
                        pass
            except Exception:
                pass

    def _close_from_bg_thread(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self.close()
        except Exception as e:
            xbmc.log('[TheIntroDB] Submit overlay close failed: {}'.format(e), xbmc.LOGWARNING)

    def _stop_poll_thread(self) -> None:
        with self._lock:
            self._closed = True

    def _dismiss_main_thread(self) -> None:
        self._stop_poll_thread()
        try:
            self.close()
        except Exception:
            pass


def show_submit_mark_overlay(label_text: str, player: Optional[xbmc.Player] = None,
                             monitor: Optional[xbmc.Monitor] = None) -> bool:
    """Show the mark overlay pill. Blocks until dismissed. Returns True if pressed."""
    mon = monitor if monitor is not None else xbmc.Monitor()
    if mon.abortRequested():
        return False
    try:
        wnd = SubmitMarkOverlay(
            'overlay.xml',
            ADDON_PATH,
            button_styles.resolve(ADDON_PATH, _OVERLAY_RES),
            _OVERLAY_RES,
            label_text=label_text,
            player=player,
            monitor=monitor,
        )
        wnd.doModal()
        pressed = wnd.button_pressed
        del wnd
        return pressed
    except Exception as e:
        xbmc.log('[TheIntroDB] Submit overlay error: {}'.format(e), xbmc.LOGERROR)
        return False
