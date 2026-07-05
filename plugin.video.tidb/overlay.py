# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
# skip intro button windowxml — background thread closes when playhead passes intro end
import os
import threading
import time
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
from typing import Optional, Callable

ADDON = xbmcaddon.Addon()
ADDON_PATH: str = ADDON.getAddonInfo('path')
# Must match the last argument to SkipOverlay / WindowXMLDialog (folder under resources/skins/default/).


def _detect_res() -> str:
    try:
        height = xbmc.getScreenHeight()
        return '1080i' if height >= 1080 else '720p'
    except Exception:
        return '1080i'


_OVERLAY_RES = _detect_res()
_BG_IMAGE_SHADOW = 3003
_BG_IMAGE_FILL = 3004

# String IDs for localization
STR_SKIP_INTRO = 32001
STR_SKIP_RECAP = 32003
STR_SKIP_CREDITS = 32004
STR_SKIP_PREVIEW = 32005
STR_NEXT_EPISODE = 32012

# must match overlay.xml window id
OVERLAY_WINDOW_ID = 14000

ACTION_SELECT = 7
ACTION_PREVIOUS_MENU = 10
ACTION_BACK = 92
BUTTON_ID = 3001

_POLL_INTERVAL = 0.5
_START_POLL_INTERVAL = 0.25
_CLOCK_ADVANCE_EPSILON = 0.05
_DEFAULT_DISPLAY_SECONDS = 0  # 0 = keep until segment ends; users can override via General setting 'button_display_seconds'


def _rounded_rect_texture_path() -> str:
    joined = os.path.join(
        ADDON_PATH, 'resources', 'skins', 'default', _OVERLAY_RES, 'rounded_rect.png')
    return xbmcvfs.translatePath(joined)


class SkipOverlay(xbmcgui.WindowXMLDialog):

    def __new__(cls, xml_file: str, addon_path: str, skin: str, res: str,
                callback: Optional[Callable[[], None]] = None, intro_end: Optional[float] = None,
                player: Optional[xbmc.Player] = None, monitor: Optional[xbmc.Monitor] = None,
                segment_type: str = 'intro', segment_index: int = 0) -> 'SkipOverlay':
        return super(SkipOverlay, cls).__new__(cls, xml_file, addon_path, skin, res)  # type: ignore[call-arg]

    def __init__(self, xml_file: str, addon_path: str, skin: str, res: str,
                 callback: Optional[Callable[[], None]] = None, intro_end: Optional[float] = None,
                 player: Optional[xbmc.Player] = None, monitor: Optional[xbmc.Monitor] = None,
                 segment_type: str = 'intro', segment_index: int = 0) -> None:
        super(SkipOverlay, self).__init__(xml_file, addon_path, skin, res)
        self._skip_pressed: bool = False
        self._callback: Optional[Callable[[], None]] = callback
        self._intro_end: Optional[float] = intro_end
        self._player: Optional[xbmc.Player] = player
        self._monitor: Optional[xbmc.Monitor] = monitor
        self._poll_thread: Optional[threading.Thread] = None
        self._closed: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._segment_type: str = segment_type
        self._segment_index: int = segment_index
        self._display_deadline: Optional[float] = None

    @property
    def skip_pressed(self) -> bool:
        return self._skip_pressed

    def _get_segment_button_text(self, segment_type: str) -> str:
        """Get the appropriate button text for the segment type."""
        segment_texts = {
            'intro': ADDON.getLocalizedString(STR_SKIP_INTRO),
            'recap': ADDON.getLocalizedString(STR_SKIP_RECAP),
            'credits': ADDON.getLocalizedString(STR_SKIP_CREDITS),
            'preview': ADDON.getLocalizedString(STR_SKIP_PREVIEW),
            'next_episode': ADDON.getLocalizedString(STR_NEXT_EPISODE)
        }
        base_text = segment_texts.get(segment_type, ADDON.getLocalizedString(STR_SKIP_INTRO))
        
        return base_text

    def onInit(self) -> None:
        mon = self._monitor if self._monitor is not None else xbmc.Monitor()
        if mon.abortRequested():
            self._dismiss_main_thread()
            return
        
        # Reload pill textures by absolute path (relative paths sometimes fail for addon WindowXML on some platforms).
        try:
            tex = _rounded_rect_texture_path()
            self.getControl(_BG_IMAGE_SHADOW).setImage(tex)
            self.getControl(_BG_IMAGE_FILL).setImage(tex)
        except Exception as e:
            xbmc.log('[TheIntroDB] Overlay background textures: {}'.format(e), xbmc.LOGWARNING)
        
        # Set dynamic button text based on segment type
        try:
            button_text = self._get_segment_button_text(self._segment_type)
            button_control = self.getControl(BUTTON_ID)
            if isinstance(button_control, xbmcgui.ControlButton):
                button_control.setLabel(button_text)
        except Exception as e:
            xbmc.log('[TheIntroDB] Failed to set button text: {}'.format(e), xbmc.LOGWARNING)
        
        try:
            self.setFocusId(BUTTON_ID)
        except Exception:
            pass
        if self._intro_end is not None and self._player is not None:
            # Read configurable display duration (0 = keep until segment ends)
            try:
                display_secs = int(ADDON.getSetting('button_display_seconds'))
            except (ValueError, TypeError):
                display_secs = _DEFAULT_DISPLAY_SECONDS
            if display_secs > 0:
                self._display_deadline = time.time() + display_secs
            else:
                self._display_deadline = None  # keep until segment ends
            self._poll_thread = threading.Thread(target=self._poll_loop)
            self._poll_thread.daemon = True
            self._poll_thread.start()

    def onClick(self, controlId: int) -> None:
        if controlId == BUTTON_ID:
            self._do_skip()

    def onAction(self, action: xbmcgui.Action) -> None:
        aid = action.getId()
        if aid == ACTION_SELECT:
            try:
                if self.getFocusId() == BUTTON_ID:
                    self._do_skip()
            except Exception:
                pass
            return
        if aid in (ACTION_PREVIOUS_MENU, ACTION_BACK):
            self._dismiss_main_thread()

    def _do_skip(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._skip_pressed = True
        self._stop_poll_thread()
        if self._callback:
            try:
                self._callback()
            except Exception:
                pass
        self._dismiss_main_thread()

    def _poll_loop(self) -> None:
        # close from worker thread using dialog.close builtin — kodi does not like gui from random threads otherwise
        mon = self._monitor if self._monitor is not None else xbmc.Monitor()
        # No immediate getTime check: playback advances while WindowXML loads; that race closed the dialog instantly.
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
                pl = self._player
                if self._display_deadline is not None and time.time() >= self._display_deadline:
                    self._close_from_bg_thread()
                    return
                if pl and pl.isPlaying() and self._intro_end is not None:
                    current_time = pl.getTime()
                    if current_time >= self._intro_end:
                        self._close_from_bg_thread()
                        return
                elif pl and not pl.isPlaying():
                    self._close_from_bg_thread()
                    return
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
            xbmc.log('[TheIntroDB] Overlay close failed: {}'.format(e), xbmc.LOGWARNING)

    def _stop_poll_thread(self) -> None:
        with self._lock:
            self._closed = True

    def _dismiss_main_thread(self) -> None:
        self._stop_poll_thread()
        try:
            self.close()
        except Exception:
            pass


def show_skip_overlay(callback: Optional[Callable[[], None]] = None, intro_end: Optional[float] = None,
                      player: Optional[xbmc.Player] = None, monitor: Optional[xbmc.Monitor] = None,
                      segment_type: str = 'intro', segment_index: int = 0) -> bool:
    # blocks until window closes; true if user hit skip
    mon = monitor if monitor is not None else xbmc.Monitor()
    if mon.abortRequested():
        return False
    if not _wait_for_playback_clock(player, mon, intro_end):
        return False
    try:
        wnd = SkipOverlay(
            'overlay.xml',
            ADDON_PATH,
            'default',
            _OVERLAY_RES,
            callback=callback,
            intro_end=intro_end,
            player=player,
            monitor=monitor,
            segment_type=segment_type,
            segment_index=segment_index,
        )
        wnd.doModal()
        pressed = wnd.skip_pressed
        del wnd
        return pressed
    except Exception as e:
        xbmc.log('[TheIntroDB] Overlay error: {}'.format(e), xbmc.LOGERROR)
        return False


def _wait_for_playback_clock(player: Optional[xbmc.Player], monitor: xbmc.Monitor,
                             intro_end: Optional[float]) -> bool:
    """Wait until Kodi's playback clock is advancing before opening the overlay."""
    if player is None:
        return True

    previous_time: Optional[float] = None

    while not monitor.abortRequested():
        try:
            playback_started = getattr(player, 'playback_started', True)
            if not playback_started:
                return False

            if player.isPlaying():
                current_time = player.getTime()
                if intro_end is not None and current_time >= intro_end:
                    return False
                if previous_time is not None and current_time > previous_time + _CLOCK_ADVANCE_EPSILON:
                    return True
                previous_time = current_time
            else:
                previous_time = None
        except Exception:
            previous_time = None

        if monitor.waitForAbort(_START_POLL_INTERVAL):
            return False

    return False
