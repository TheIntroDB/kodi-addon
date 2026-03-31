"""Service entry: watches playback, hits TheIntroDB, shows skip UI or auto-skips."""
import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from player import IntroSkipPlayer
import skipper
import storage
import overlay as overlay_mod
import introdb

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
_PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
_SETUP_TIP_FLAG = os.path.join(_PROFILE, 'setup_tip_shown')


class IntroSkipMonitor(xbmc.Monitor):
    pass


def _notify(message, duration=3000):
    xbmc.executebuiltin('Notification({}, {}, {})'.format(ADDON_NAME, message, duration))


def _debug_osd(message):
    if ADDON.getSetting('debug_osd') == 'true':
        xbmc.executebuiltin('Notification(IntroSkip, {}, 1500)'.format(message))


def _bool(key):
    return ADDON.getSetting(key) == 'true'


def _maybe_show_setup_tip(monitor):
    # one-time dialog after install — don't block Kodi before the UI is up
    if os.path.isfile(_SETUP_TIP_FLAG):
        return
    if monitor.waitForAbort(3):
        return
    try:
        if not os.path.isdir(_PROFILE):
            os.makedirs(_PROFILE)
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            'Intro times come from TheIntroDB (theintrodb.org).[CR][CR]'
            'Get your API key on that site, then open this addon settings and '
            'paste it under TheIntroDB → API Key.[CR][CR]'
            'Does not work without an API key as of yet.',
        )
        with open(_SETUP_TIP_FLAG, 'w') as f:
            f.write('1')
    except Exception as e:
        xbmc.log('[IntroSkip] setup tip dialog: {}'.format(e), xbmc.LOGWARNING)


def _run_service():
    monitor = IntroSkipMonitor()
    player = IntroSkipPlayer()

    xbmc.log('[IntroSkip] Service started', xbmc.LOGINFO)
    _maybe_show_setup_tip(monitor)

    skip_done = False
    last_file = None

    while not monitor.abortRequested():
        if monitor.waitForAbort(1.0):
            break

        if not player.playback_started:
            if skip_done or last_file:
                skip_done = False
                last_file = None
            continue

        if not player.is_tv_content:
            continue

        if skip_done:
            continue

        filename = player.filename
        if not filename:
            continue

        if filename == last_file:
            continue

        last_file = filename
        skip_done = False

        _debug_osd('Monitoring: {}'.format(filename[-40:]))

        introdb_on = _bool('introdb_enabled')
        auto_skip = _bool('auto_skip')

        media_ids = player.get_media_ids()
        tmdb = media_ids.get('tmdb_id')
        imdb = media_ids.get('imdb_id')
        m_season = media_ids.get('season')
        m_episode = media_ids.get('episode')
        m_movie = media_ids.get('is_movie', False)

        xbmc.log('[IntroSkip] Media IDs: tmdb={} imdb={} S{}E{} movie={}'.format(
            tmdb, imdb, m_season, m_episode, m_movie), xbmc.LOGINFO)
        _debug_osd('tmdb={} imdb={} S{}E{}'.format(
            tmdb or '-', imdb or '-', m_season or '?', m_episode or '?'))

        api_start = None
        api_end = None

        if introdb_on and tmdb:
            api_start, api_end = introdb.query_intro(
                tmdb_id=tmdb,
                season=m_season,
                episode=m_episode,
                is_movie=m_movie,
            )

        if api_start is not None and api_end is not None:
            msg = 'TheIntroDB: {:.1f}s -> {:.1f}s'.format(api_start, api_end)
            xbmc.log('[IntroSkip] {}'.format(msg), xbmc.LOGINFO)
            _debug_osd(msg)

            _wait_for_time(monitor, player, api_start)

            if not player.isPlaying():
                continue

            if auto_skip:
                skipper.execute_skip(player, api_start, api_end, filename)
                skip_done = True
                _debug_osd('Auto-skipped intro')
                xbmc.log('[IntroSkip] Auto-skipped to {:.1f}s'.format(api_end), xbmc.LOGINFO)
            else:
                if monitor.abortRequested():
                    break
                xbmc.log('[IntroSkip] Showing skip overlay', xbmc.LOGINFO)
                pressed = overlay_mod.show_skip_overlay(
                    intro_end=api_end,
                    player=player,
                    monitor=monitor,
                )
                if pressed:
                    xbmc.log('[IntroSkip] User pressed Skip Intro', xbmc.LOGINFO)
                    skipper.execute_skip(player, api_start, api_end, filename)
                    _debug_osd('Skipped to {:.1f}s'.format(api_end))
                skip_done = True
        else:
            if tmdb:
                _debug_osd('TheIntroDB: no data for this episode')
            elif imdb:
                _debug_osd('Need TMDB ID (only have IMDB)')
            else:
                _debug_osd('No media IDs found')

    xbmc.log('[IntroSkip] Service stopped', xbmc.LOGINFO)


def _wait_for_time(monitor, player, target_time):
    # wait until playback hits intro start, or bail if they stop/pause
    while not monitor.abortRequested():
        if monitor.waitForAbort(0.5):
            return
        if not player.isPlaying():
            return
        try:
            current = player.getTime()
        except Exception:
            return
        if current >= target_time - 1:
            return


def _handle_reset():
    storage.reset_all()
    _notify('Learned data reset')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'reset_data':
        _handle_reset()
    else:
        _run_service()
