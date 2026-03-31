"""Skip button dialog. Poll thread closes it with Dialog.Close so I don't poke GUI from the wrong thread."""
import threading
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')

OVERLAY_WINDOW_ID = 14000  # matches overlay.xml

ACTION_SELECT = 7
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_PREVIOUS_MENU = 10
ACTION_BACK = 92
BUTTON_ID = 3001

_POLL_INTERVAL = 0.5


class SkipOverlay(xbmcgui.WindowXMLDialog):

    def __new__(cls, xml_file, addon_path, skin, res,
                callback=None, intro_end=None, player=None, monitor=None):
        return super(SkipOverlay, cls).__new__(cls, xml_file, addon_path, skin, res)

    def __init__(self, xml_file, addon_path, skin, res,
                 callback=None, intro_end=None, player=None, monitor=None):
        super(SkipOverlay, self).__init__(xml_file, addon_path, skin, res)
        self._skip_pressed = False
        self._callback = callback
        self._intro_end = intro_end
        self._player = player
        self._monitor = monitor
        self._poll_thread = None
        self._closed = False
        self._lock = threading.Lock()

    @property
    def skip_pressed(self):
        return self._skip_pressed

    def onInit(self):
        mon = self._monitor if self._monitor is not None else xbmc.Monitor()
        if mon.abortRequested():
            self._dismiss_main_thread()
            return
        try:
            self.setFocusId(BUTTON_ID)
        except Exception:
            pass
        if self._intro_end is not None and self._player is not None:
            self._poll_thread = threading.Thread(target=self._poll_loop)
            self._poll_thread.daemon = True
            self._poll_thread.start()

    def onClick(self, controlId):
        if controlId == BUTTON_ID:
            self._do_skip()

    def onAction(self, action):
        aid = action.getId()
        if aid in (ACTION_SELECT, ACTION_MOUSE_LEFT_CLICK):
            try:
                if self.getFocusId() == BUTTON_ID:
                    self._do_skip()
            except Exception:
                pass
            return
        if aid in (ACTION_PREVIOUS_MENU, ACTION_BACK):
            self._dismiss_main_thread()

    def _do_skip(self):
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

    def _poll_loop(self):
        mon = self._monitor if self._monitor is not None else xbmc.Monitor()
        # edge case: intro already over when the dialog opens
        try:
            pl = self._player
            if pl and pl.isPlaying() and pl.getTime() >= self._intro_end:
                self._close_from_bg_thread()
                return
        except Exception:
            pass
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
                if pl and pl.isPlaying() and pl.getTime() >= self._intro_end:
                    self._close_from_bg_thread()
                    return
            except Exception:
                pass

    def _close_from_bg_thread(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
        xbmc.executebuiltin('Dialog.Close({},{})'.format(OVERLAY_WINDOW_ID, 'true'))

    def _stop_poll_thread(self):
        with self._lock:
            self._closed = True

    def _dismiss_main_thread(self):
        self._stop_poll_thread()
        try:
            self.close()
        except Exception:
            pass


def show_skip_overlay(callback=None, intro_end=None, player=None, monitor=None):
    # blocks until close; True if they actually skipped
    mon = monitor if monitor is not None else xbmc.Monitor()
    if mon.abortRequested():
        return False
    try:
        wnd = SkipOverlay(
            'overlay.xml',
            ADDON_PATH,
            'default',
            '1080i',
            callback=callback,
            intro_end=intro_end,
            player=player,
            monitor=monitor,
        )
        wnd.doModal()
        pressed = wnd.skip_pressed
        del wnd
        return pressed
    except Exception as e:
        xbmc.log('[IntroSkip] Overlay error: {}'.format(e), xbmc.LOGERROR)
        return False
