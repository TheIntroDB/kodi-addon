# kodi service entry: poll playback, query theintrodb, show skip ui or auto-seek
import xbmc
import xbmcaddon

from player import IntroSkipPlayer
import skipper
import overlay as overlay_mod
import introdb

ADDON = xbmcaddon.Addon()
_ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')


class IntroSkipMonitor(xbmc.Monitor):
    pass


def _debug_osd(message):
    # optional toast spam for debugging
    if ADDON.getSetting('debug_osd') == 'true':
        xbmc.executebuiltin('Notification(IntroSkip, {}, 1500)'.format(message))


def _fresh_bool(key):
    # read setting again from disk so gui changes apply without restart
    try:
        return xbmcaddon.Addon(_ADDON_ID).getSetting(key) == 'true'
    except Exception:
        return ADDON.getSetting(key) == 'true'

def _run_service():
    monitor = IntroSkipMonitor()
    player = IntroSkipPlayer()

    xbmc.log('[IntroSkip] Service started', xbmc.LOGINFO)

    # which file we already finished intro handling for; cleared when playback stops
    last_file = None

    while not monitor.abortRequested():
        if monitor.waitForAbort(1.0):
            break

        if not player.playback_started:
            last_file = None
            continue

        # skip movies that do not look like tv; player decides
        if not player.is_tv_content:
            continue

        filename = player.filename
        if not filename:
            continue

        # same file as last successful pass — do not run again
        if filename == last_file:
            continue

        _debug_osd('Monitoring: {}'.format(filename[-40:]))

        introdb_on = _fresh_bool('introdb_enabled')
        auto_skip = _fresh_bool('auto_skip')

        if ADDON.getSetting('debug_logging') == 'true':
            _raw = xbmcaddon.Addon(_ADDON_ID).getSetting('introdb_enabled')
            xbmc.log(
                '[IntroSkip] introdb_enabled raw={!r} lookups_on={}'.format(_raw, introdb_on),
                xbmc.LOGINFO,
            )

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

        if introdb_on and (tmdb or imdb):
            api_start, api_end = introdb.query_intro(
                tmdb_id=tmdb,
                imdb_id=imdb,
                season=m_season,
                episode=m_episode,
                is_movie=m_movie,
            )

        if api_start is not None and api_end is not None:
            msg = 'TheIntroDB: {:.1f}s -> {:.1f}s'.format(api_start, api_end)
            xbmc.log('[IntroSkip] {}'.format(msg), xbmc.LOGINFO)
            _debug_osd(msg)

            # resume or seek landed past intro — nothing to show
            if _playback_past_intro_end(player, api_end):
                xbmc.log(
                    '[IntroSkip] Already past intro window; skipping UI',
                    xbmc.LOGINFO,
                )
                last_file = filename
                continue

            # wait until roughly intro start so we do not pop the overlay at t=0
            _wait_for_time(monitor, player, api_start)

            if not player.isPlaying():
                last_file = filename
                continue

            if _playback_past_intro_end(player, api_end):
                xbmc.log(
                    '[IntroSkip] Past intro end after wait; skipping UI',
                    xbmc.LOGINFO,
                )
                last_file = filename
                continue

            if auto_skip:
                skipper.execute_skip(player, api_start, api_end, filename)
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
            last_file = filename
        else:
            if introdb_on:
                if tmdb or imdb:
                    _debug_osd('TheIntroDB: no intro for this item')
                else:
                    _debug_osd('No TMDB or IMDb id')
            last_file = filename

    xbmc.log('[IntroSkip] Service stopped', xbmc.LOGINFO)


def _playback_past_intro_end(player, api_end, margin=0.25):
    try:
        if not player.isPlaying():
            return True
        return player.getTime() >= (api_end - margin)
    except Exception:
        return True


def _wait_for_time(monitor, player, target_time):
    # spin until intro start is near, or playback stops
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


if __name__ == '__main__':
    _run_service()
