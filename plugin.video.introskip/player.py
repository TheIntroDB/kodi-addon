# subclasses xbmc.player — path, whether we treat this as tv-ish content, scrape ids for api
import json
import re
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()


class IntroSkipPlayer(xbmc.Player):
    def __init__(self):
        super(IntroSkipPlayer, self).__init__()
        self._playback_started = False
        self._filename = None
        self._is_tv = False
        self._is_video = False

    @property
    def playback_started(self):
        return self._playback_started

    @property
    def filename(self):
        return self._filename

    @property
    def is_tv_content(self):
        return self._is_tv

    @property
    def is_video(self):
        return self._is_video

    def onAVStarted(self):
        self._playback_started = True
        try:
            self._filename = self.getPlayingFile()
        except Exception:
            self._filename = None

        self._is_video = self._check_is_video()
        self._is_tv = self._detect_tv_content()
        xbmc.log('[IntroSkip] Playback started: {} (tv={}, video={})'.format(
            self._filename, self._is_tv, self._is_video), xbmc.LOGINFO)

    def onPlayBackStopped(self):
        self._reset()

    def onPlayBackEnded(self):
        self._reset()

    def onPlayBackError(self):
        self._reset()

    def _reset(self):
        xbmc.log('[IntroSkip] Playback ended/stopped', xbmc.LOGINFO)
        self._playback_started = False
        self._filename = None
        self._is_tv = False
        self._is_video = False

    def _check_is_video(self):
        try:
            return self.isPlayingVideo()
        except Exception:
            return False

    def _detect_tv_content(self):
        # episodes, sxxeyy in path, or long video — rough filter for streamers
        if not self._is_video:
            return False

        try:
            tag = self.getVideoInfoTag()
            if tag.getSeason() > 0 and tag.getEpisode() > 0:
                return True
            media_type = tag.getMediaType()
            if media_type == 'episode':
                return True
        except Exception:
            pass

        if self._filename:
            if re.search(r'[Ss]\d{1,2}[Ee]\d{1,2}', self._filename):
                return True

        min_duration = 600
        try:
            total = self.getTotalTime()
            if total < min_duration:
                return False
        except Exception:
            pass

        return True

    def get_media_ids(self):
        # json-rpc first (addons often set ids there), then videoinfotag
        ids = {
            'imdb_id': None,
            'tmdb_id': None,
            'season': None,
            'episode': None,
            'is_movie': False,
        }

        self._ids_from_jsonrpc(ids)
        self._ids_from_infotag(ids)

        xbmc.log('[IntroSkip] Extracted media IDs: {}'.format(ids), xbmc.LOGINFO)
        return ids

    def _active_video_player_id(self):
        try:
            r = json.loads(xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.GetActivePlayers","id":1}'))
            for p in r.get('result') or []:
                if p.get('type') == 'video':
                    return int(p.get('playerid', 0))
            res = r.get('result') or []
            if res:
                return int(res[0].get('playerid', 1))
        except Exception:
            pass
        return 1

    def _ids_from_jsonrpc(self, ids):
        try:
            pid = self._active_video_player_id()
            query = json.dumps({
                'jsonrpc': '2.0',
                'method': 'Player.GetItem',
                'params': {
                    'playerid': pid,
                    'properties': [
                        'uniqueid', 'imdbnumber', 'season', 'episode',
                        'showtitle', 'title', 'type'
                    ]
                },
                'id': 1
            })
            response = json.loads(xbmc.executeJSONRPC(query))
            item = response.get('result', {}).get('item', {})

            if ADDON.getSetting('debug_logging') == 'true':
                xbmc.log('[IntroSkip] JSON-RPC item: type={} uniqueid={} imdbnumber={}'.format(
                    item.get('type'), item.get('uniqueid'), item.get('imdbnumber')),
                    xbmc.LOGINFO)

            unique = item.get('uniqueid', {})
            if isinstance(unique, dict):
                tmdb_val = unique.get('tmdb') or unique.get('themoviedb')
                if tmdb_val:
                    try:
                        if int(tmdb_val) > 0:
                            ids['tmdb_id'] = str(tmdb_val)
                    except (ValueError, TypeError):
                        pass

                imdb_val = unique.get('imdb')
                if imdb_val and str(imdb_val).startswith('tt'):
                    ids['imdb_id'] = str(imdb_val)

                if not ids['tmdb_id']:
                    tmdb_show = unique.get('tmdbshow') or unique.get('tmdb_show')
                    if tmdb_show:
                        try:
                            if int(tmdb_show) > 0:
                                ids['tmdb_id'] = str(tmdb_show)
                        except (ValueError, TypeError):
                            pass

            imdbnumber = item.get('imdbnumber')
            if imdbnumber:
                if str(imdbnumber).startswith('tt') and not ids['imdb_id']:
                    ids['imdb_id'] = str(imdbnumber)
                elif not ids['tmdb_id']:
                    try:
                        if int(imdbnumber) > 0:
                            ids['tmdb_id'] = str(imdbnumber)
                    except (ValueError, TypeError):
                        pass

            if item.get('season') and item['season'] > 0:
                ids['season'] = item['season']
            if item.get('episode') and item['episode'] > 0:
                ids['episode'] = item['episode']

            item_type = item.get('type', '')
            if item_type == 'movie':
                ids['is_movie'] = True
            elif item_type == 'episode':
                ids['is_movie'] = False

        except Exception as e:
            xbmc.log('[IntroSkip] JSON-RPC Player.GetItem failed: {}'.format(e),
                      xbmc.LOGWARNING)

    def _ids_from_infotag(self, ids):
        try:
            tag = self.getVideoInfoTag()
        except Exception:
            return

        if not ids['imdb_id']:
            try:
                imdb = tag.getIMDBNumber()
                if imdb and str(imdb).startswith('tt'):
                    ids['imdb_id'] = str(imdb)
            except Exception:
                pass

        if not ids['tmdb_id']:
            try:
                tmdb = tag.getUniqueID('tmdb')
                if tmdb:
                    val = str(tmdb)
                    if val and not val.startswith('tt'):
                        try:
                            if int(val) > 0:
                                ids['tmdb_id'] = val
                        except (ValueError, TypeError):
                            pass
            except Exception:
                pass

        if not ids['tmdb_id']:
            try:
                imdb_val = tag.getIMDBNumber()
                if imdb_val and not str(imdb_val).startswith('tt'):
                    try:
                        if int(imdb_val) > 0:
                            ids['tmdb_id'] = str(imdb_val)
                    except (ValueError, TypeError):
                        pass
            except Exception:
                pass

        if not ids['season'] or ids['season'] <= 0:
            try:
                s = tag.getSeason()
                if s and s > 0:
                    ids['season'] = s
            except Exception:
                pass

        if not ids['episode'] or ids['episode'] <= 0:
            try:
                e = tag.getEpisode()
                if e and e > 0:
                    ids['episode'] = e
            except Exception:
                pass

        try:
            media_type = tag.getMediaType()
            if media_type == 'movie':
                ids['is_movie'] = True
            elif media_type == 'episode':
                ids['is_movie'] = False
        except Exception:
            pass
