# subclasses xbmc.player — path, whether we treat this as tv-ish content, scrape ids for api
import json
import re
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()


class TIDBPlayer(xbmc.Player):
    def __init__(self):
        super(TIDBPlayer, self).__init__()
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
        xbmc.log('[TheIntroDB] Playback started: {} (tv={}, video={})'.format(
            self._filename, self._is_tv, self._is_video), xbmc.LOGINFO)

    def onPlayBackStopped(self):
        self._reset()

    def onPlayBackEnded(self):
        self._reset()

    def onPlayBackError(self):
        self._reset()

    def _reset(self):
        xbmc.log('[TheIntroDB] Playback ended/stopped', xbmc.LOGINFO)
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

        xbmc.log('[TheIntroDB] Extracted media IDs: {}'.format(ids), xbmc.LOGINFO)
        return ids

    def get_next_episode(self):
        item = self._get_current_player_item()
        if not item or item.get('type') != 'episode':
            return None

        try:
            tvshowid = int(item.get('tvshowid'))
            current_season = int(item.get('season'))
            current_episode = int(item.get('episode'))
        except (TypeError, ValueError):
            return None

        response = self._jsonrpc('VideoLibrary.GetEpisodes', {
            'tvshowid': tvshowid,
            'properties': ['season', 'episode', 'title'],
            'sort': {'method': 'episode', 'order': 'ascending'},
        })
        episodes = (response or {}).get('result', {}).get('episodes') or []
        current_key = (current_season, current_episode)
        next_episode = None
        next_key = None

        for episode in episodes:
            episodeid = episode.get('episodeid')
            try:
                season = int(episode.get('season'))
                number = int(episode.get('episode'))
            except (TypeError, ValueError):
                continue
            if not episodeid:
                continue

            episode_key = (season, number)
            if episode_key <= current_key:
                continue
            if next_key is None or episode_key < next_key:
                next_key = episode_key
                next_episode = {
                    'episodeid': int(episodeid),
                    'season': season,
                    'episode': number,
                    'title': episode.get('title') or '',
                }

        if next_episode and ADDON.getSetting('debug_logging') == 'true':
            xbmc.log(
                '[TheIntroDB] Next episode found: S{}E{} {}'.format(
                    next_episode['season'],
                    next_episode['episode'],
                    next_episode['title'],
                ),
                xbmc.LOGINFO,
            )

        return next_episode

    def play_next_episode(self, next_episode=None):
        if next_episode is None:
            next_episode = self.get_next_episode()
        if not next_episode:
            return False

        response = self._jsonrpc('Player.Open', {
            'item': {'episodeid': next_episode['episodeid']},
        })
        if response and 'error' not in response:
            return True

        if ADDON.getSetting('debug_logging') == 'true':
            xbmc.log('[TheIntroDB] Failed to open next episode: {}'.format(response), xbmc.LOGWARNING)
        return False

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

    def _get_current_player_item(self):
        response = self._jsonrpc('Player.GetItem', {
            'playerid': self._active_video_player_id(),
            'properties': [
                'id', 'tvshowid', 'season', 'episode', 'showtitle', 'title', 'type',
            ],
        })
        return (response or {}).get('result', {}).get('item') or {}

    def _jsonrpc(self, method, params=None):
        try:
            payload = {'jsonrpc': '2.0', 'method': method, 'id': 1}
            if params is not None:
                payload['params'] = params
            return json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
        except Exception:
            return None

    def _extract_numeric_id(self, value):
        try:
            s = str(value).strip()
            if not s:
                return None
            if int(s) > 0:
                return s
        except (ValueError, TypeError):
            return None
        return None

    def _extract_tmdb_from_uniqueid(self, unique, keys):
        if not isinstance(unique, dict):
            return None
        for key in keys:
            val = self._extract_numeric_id(unique.get(key))
            if val:
                return val
        return None

    def _apply_uniqueid_dict(self, unique, ids):
        if not isinstance(unique, dict):
            return

        if not ids.get('tmdb_id'):
            tmdb_val = unique.get('tmdb') or unique.get('themoviedb')
            if tmdb_val:
                try:
                    if int(tmdb_val) > 0:
                        ids['tmdb_id'] = str(tmdb_val)
                except (ValueError, TypeError):
                    pass

        if not ids.get('imdb_id'):
            imdb_val = unique.get('imdb')
            if imdb_val and str(imdb_val).startswith('tt'):
                ids['imdb_id'] = str(imdb_val)

        if not ids.get('tmdb_id'):
            tmdb_show = unique.get('tmdbshow') or unique.get('tmdb_show')
            if tmdb_show:
                try:
                    if int(tmdb_show) > 0:
                        ids['tmdb_id'] = str(tmdb_show)
                except (ValueError, TypeError):
                    pass

    def _apply_episode_item_uniqueid_dict(self, unique, ids):
        if not isinstance(unique, dict):
            return

        if not ids.get('tmdb_id'):
            tmdb_show = unique.get('tmdbshow') or unique.get('tmdb_show')
            if tmdb_show:
                try:
                    if int(tmdb_show) > 0:
                        ids['tmdb_id'] = str(tmdb_show)
                except (ValueError, TypeError):
                    pass

        if not ids.get('imdb_id'):
            imdb_val = unique.get('imdb')
            if imdb_val and str(imdb_val).startswith('tt'):
                ids['imdb_id'] = str(imdb_val)

    def _tvshow_ids_from_library(self, tvshowid, ids, force_tmdb=False):
        try:
            tvshowid_int = int(tvshowid)
        except (ValueError, TypeError):
            return

        r = self._jsonrpc('VideoLibrary.GetTVShowDetails', {
            'tvshowid': tvshowid_int,
            'properties': ['uniqueid', 'imdbnumber', 'title', 'year'],
        })
        details = (r or {}).get('result', {}).get('tvshowdetails') or {}
        unique = details.get('uniqueid')
        show_tmdb = self._extract_tmdb_from_uniqueid(unique, ('tmdb', 'themoviedb', 'tmdbshow', 'tmdb_show'))
        if show_tmdb and (force_tmdb or not ids.get('tmdb_id')):
            old = ids.get('tmdb_id')
            ids['tmdb_id'] = show_tmdb
            if ADDON.getSetting('debug_logging') == 'true':
                xbmc.log('[TheIntroDB] TV show TMDB resolved: {} -> {} (uniqueid={})'.format(
                    old or '-', show_tmdb, unique), xbmc.LOGINFO)

        if not ids.get('imdb_id'):
            imdb_unique = (unique or {}).get('imdb') if isinstance(unique, dict) else None
            if imdb_unique and str(imdb_unique).startswith('tt'):
                ids['imdb_id'] = str(imdb_unique)

        imdbnumber = details.get('imdbnumber')
        if imdbnumber and str(imdbnumber).startswith('tt') and not ids.get('imdb_id'):
            ids['imdb_id'] = str(imdbnumber)

    def _tvshow_ids_by_title(self, title, ids, force_tmdb=False):
        if not title:
            return

        r = self._jsonrpc('VideoLibrary.GetTVShows', {
            'filter': {'field': 'title', 'operator': 'is', 'value': str(title)},
            'properties': ['title', 'uniqueid', 'imdbnumber', 'year'],
        })
        tvshows = (r or {}).get('result', {}).get('tvshows') or []
        if not tvshows:
            return

        pick = None
        for t in tvshows:
            if str(t.get('title') or '').strip().lower() == str(title).strip().lower():
                pick = t
                break
        if pick is None:
            pick = tvshows[0]

        unique = pick.get('uniqueid')
        show_tmdb = self._extract_tmdb_from_uniqueid(unique, ('tmdb', 'themoviedb', 'tmdbshow', 'tmdb_show'))
        if show_tmdb and (force_tmdb or not ids.get('tmdb_id')):
            old = ids.get('tmdb_id')
            ids['tmdb_id'] = show_tmdb
            if ADDON.getSetting('debug_logging') == 'true':
                xbmc.log('[TheIntroDB] TV show TMDB resolved (title match): {} -> {} (title={} uniqueid={})'.format(
                    old or '-', show_tmdb, title, unique), xbmc.LOGINFO)

        if not ids.get('imdb_id'):
            imdb_unique = (unique or {}).get('imdb') if isinstance(unique, dict) else None
            if imdb_unique and str(imdb_unique).startswith('tt'):
                ids['imdb_id'] = str(imdb_unique)

        imdbnumber = pick.get('imdbnumber')
        if imdbnumber and str(imdbnumber).startswith('tt') and not ids.get('imdb_id'):
            ids['imdb_id'] = str(imdbnumber)

    def _ids_from_jsonrpc(self, ids):
        try:
            pid = self._active_video_player_id()
            response = self._jsonrpc('Player.GetItem', {
                'playerid': pid,
                'properties': [
                    'id', 'tvshowid', 'uniqueid', 'imdbnumber', 'season', 'episode',
                    'showtitle', 'title', 'type',
                ],
            })
            item = (response or {}).get('result', {}).get('item') or {}

            if ADDON.getSetting('debug_logging') == 'true':
                xbmc.log('[TheIntroDB] JSON-RPC item: type={} uniqueid={} imdbnumber={}'.format(
                    item.get('type'), item.get('uniqueid'), item.get('imdbnumber')),
                    xbmc.LOGINFO)

            imdbnumber = item.get('imdbnumber')
            if imdbnumber:
                if str(imdbnumber).startswith('tt') and not ids['imdb_id']:
                    ids['imdb_id'] = str(imdbnumber)

            if item.get('season') and item['season'] > 0:
                ids['season'] = item['season']
            if item.get('episode') and item['episode'] > 0:
                ids['episode'] = item['episode']

            item_type = item.get('type', '')
            if item_type == 'movie':
                ids['is_movie'] = True
                self._apply_uniqueid_dict(item.get('uniqueid'), ids)
            elif item_type == 'episode':
                ids['is_movie'] = False
                self._apply_episode_item_uniqueid_dict(item.get('uniqueid'), ids)
                self._tvshow_ids_from_library(item.get('tvshowid'), ids, force_tmdb=True)
                self._tvshow_ids_by_title(item.get('showtitle'), ids, force_tmdb=True)

        except Exception as e:
            xbmc.log('[TheIntroDB] JSON-RPC Player.GetItem failed: {}'.format(e),
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
                for key in ('tmdbshow', 'tmdb_show', 'themoviedb', 'tmdb'):
                    tmdb = tag.getUniqueID(key)
                    if not tmdb:
                        continue
                    val = str(tmdb)
                    if not val or val.startswith('tt'):
                        continue
                    if key in ('tmdb', 'themoviedb') and (ids.get('season') and ids.get('episode') and not ids.get('is_movie')):
                        continue
                    try:
                        if int(val) > 0:
                            ids['tmdb_id'] = val
                            break
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

        if ids.get('season') and ids.get('episode') and not ids.get('is_movie'):
            try:
                showtitle = tag.getTVShowTitle()
            except Exception:
                showtitle = None
            if showtitle:
                self._tvshow_ids_by_title(showtitle, ids, force_tmdb=True)
