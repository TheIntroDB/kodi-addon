# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
# subclasses xbmc.player — path, whether we treat this as tv-ish content, scrape ids for api
import json
import re
import xbmc
import xbmcaddon
from typing import Optional, Dict, Any, Tuple

ADDON = xbmcaddon.Addon()


class TIDBPlayer(xbmc.Player):
    def __init__(self) -> None:
        super(TIDBPlayer, self).__init__()
        self._playback_started: bool = False
        self._filename: Optional[str] = None
        self._is_tv: bool = False
        self._is_video: bool = False
        self._is_paused: bool = False
        self._pause_count: int = 0

    @property
    def playback_started(self) -> bool:
        return self._playback_started

    @property
    def filename(self) -> Optional[str]:
        return self._filename

    @property
    def is_tv_content(self) -> bool:
        return self._is_tv

    @property
    def is_video(self) -> bool:
        return self._is_video

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def pause_count(self) -> int:
        return self._pause_count

    def onAVStarted(self) -> None:
        self._playback_started = True
        try:
            self._filename = self.getPlayingFile()
        except Exception:
            self._filename = None

        self._is_video = self._check_is_video()
        self._is_tv = self._detect_tv_content()
        xbmc.log('[TheIntroDB] Playback started: {} (tv={}, video={})'.format(
            self._filename, self._is_tv, self._is_video), xbmc.LOGINFO)

    def onPlayBackStopped(self) -> None:
        self._reset()

    def onPlayBackEnded(self) -> None:
        self._reset()

    def onPlayBackError(self) -> None:
        self._reset()

    def onPlayBackPaused(self) -> None:
        self._is_paused = True
        self._pause_count += 1
        xbmc.log('[TheIntroDB] Playback paused (count={})'.format(self._pause_count), xbmc.LOGINFO)

    def onPlayBackResumed(self) -> None:
        self._is_paused = False

    def _reset(self) -> None:
        xbmc.log('[TheIntroDB] Playback ended/stopped', xbmc.LOGINFO)
        self._playback_started = False
        self._filename = None
        self._is_tv = False
        self._is_video = False
        self._is_paused = False
        self._pause_count = 0

    def _check_is_video(self) -> bool:
        try:
            return self.isPlayingVideo()
        except Exception:
            return False

    def _detect_tv_content(self) -> bool:
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

    def get_media_ids(self) -> Dict[str, Any]:
        # json-rpc first (addons often set ids there), then videoinfotag
        ids: Dict[str, Any] = {
            'imdb_id': None,
            'tmdb_id': None,
            'tvdb_id': None,
            'tvdb_episode_id': None,
            'season': None,
            'episode': None,
            'is_movie': False,
            'duration_ms': None,
        }

        self._ids_from_jsonrpc(ids)
        self._ids_from_infotag(ids)
        ids['duration_ms'] = self._get_video_duration_ms()

        # Which id lands on an episode depends on the scraper: some store the
        # episode record, others repeat the series id. Only a distinct one is a
        # useful pin — sent as tvdb_id the API would look for a series by it.
        if ids.get('tvdb_episode_id') and ids['tvdb_episode_id'] == ids.get('tvdb_id'):
            ids['tvdb_episode_id'] = None

        xbmc.log('[TheIntroDB] Extracted media IDs: {}'.format(ids), xbmc.LOGINFO)
        return ids

    def _get_video_duration_ms(self) -> Optional[int]:
        try:
            tag = self.getVideoInfoTag()
            dur = tag.getDuration()
            if dur:
                dur_sec = int(dur)
                if dur_sec > 0:
                    return dur_sec * 1000
        except Exception:
            pass

        try:
            response = self._jsonrpc('Player.GetProperties', {
                'playerid': self._active_video_player_id(),
                'properties': ['totaltime'],
            })
            totaltime = (response or {}).get('result', {}).get('totaltime') or {}
            h = int(totaltime.get('hours', 0) or 0)
            m = int(totaltime.get('minutes', 0) or 0)
            s = int(totaltime.get('seconds', 0) or 0)
            ms = int(totaltime.get('milliseconds', 0) or 0)
            total_ms = ((h * 3600 + m * 60 + s) * 1000) + ms
            if total_ms > 0:
                return total_ms
        except Exception:
            pass

        try:
            total = self.getTotalTime()
            if total:
                total_ms = int(round(float(total) * 1000.0))
                if total_ms > 0:
                    return total_ms
        except Exception:
            pass

        return None

    def get_next_episode(self) -> Optional[Dict[str, Any]]:
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
        next_episode: Optional[Dict[str, Any]] = None
        next_key: Optional[Tuple[int, int]] = None

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

    def play_next_episode(self, next_episode: Optional[Dict[str, Any]] = None) -> bool:
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

    def _active_video_player_id(self) -> int:
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

    def _get_current_player_item(self) -> Dict[str, Any]:
        response = self._jsonrpc('Player.GetItem', {
            'playerid': self._active_video_player_id(),
            'properties': [
                'id', 'tvshowid', 'season', 'episode', 'showtitle', 'title', 'type',
            ],
        })
        return (response or {}).get('result', {}).get('item') or {}

    def _jsonrpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            payload: Dict[str, Any] = {'jsonrpc': '2.0', 'method': method, 'id': 1}
            if params is not None:
                payload['params'] = params
            return json.loads(xbmc.executeJSONRPC(json.dumps(payload)))
        except Exception:
            return None

    def _extract_numeric_id(self, value: Any) -> Optional[str]:
        try:
            s = str(value).strip()
            if not s:
                return None
            if int(s) > 0:
                return s
        except (ValueError, TypeError):
            return None
        return None

    def _extract_tmdb_from_uniqueid(self, unique: Any, keys: Tuple[str, ...]) -> Optional[str]:
        if not isinstance(unique, dict):
            return None
        for key in keys:
            val = self._extract_numeric_id(unique.get(key))
            if val:
                return val
        return None

    def _apply_uniqueid_dict(self, unique: Any, ids: Dict[str, Any]) -> None:
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

        if not ids.get('tvdb_id'):
            tvdb_val = unique.get('tvdb') or unique.get('thetvdb')
            if tvdb_val:
                try:
                    if int(tvdb_val) > 0:
                        ids['tvdb_id'] = str(tvdb_val)
                except (ValueError, TypeError):
                    pass

        if not ids.get('tmdb_id'):
            tmdb_show = unique.get('tmdbshow') or unique.get('tmdb_show')
            if tmdb_show:
                try:
                    if int(tmdb_show) > 0:
                        ids['tmdb_id'] = str(tmdb_show)
                except (ValueError, TypeError):
                    pass

    def _apply_episode_item_uniqueid_dict(self, unique: Any, ids: Dict[str, Any]) -> None:
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

        # On an episode, the TVDB scraper's `tvdb` uniqueid is the episode record
        # (the series id arrives with the show's own uniqueid below).
        if not ids.get('tvdb_episode_id'):
            tvdb_val = unique.get('tvdb')
            if tvdb_val:
                try:
                    if int(tvdb_val) > 0:
                        ids['tvdb_episode_id'] = str(tvdb_val)
                except (ValueError, TypeError):
                    pass

        if not ids.get('tvdb_id'):
            tvdb_show = unique.get('tvdbshow') or unique.get('tvdb_show')
            if tvdb_show:
                try:
                    if int(tvdb_show) > 0:
                        ids['tvdb_id'] = str(tvdb_show)
                except (ValueError, TypeError):
                    pass

    def _tvshow_ids_from_library(self, tvshowid: Any, ids: Dict[str, Any], force_tmdb: bool = False) -> None:
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

        if not ids.get('tvdb_id'):
            tvdb_unique = (unique or {}).get('tvdb') if isinstance(unique, dict) else None
            if tvdb_unique:
                try:
                    if int(tvdb_unique) > 0:
                        ids['tvdb_id'] = str(tvdb_unique)
                except (ValueError, TypeError):
                    pass

        imdbnumber = details.get('imdbnumber')
        if imdbnumber and str(imdbnumber).startswith('tt') and not ids.get('imdb_id'):
            ids['imdb_id'] = str(imdbnumber)

    def _tvshow_ids_by_title(self, title: Optional[str], ids: Dict[str, Any], force_tmdb: bool = False) -> None:
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

        if not ids.get('tvdb_id'):
            tvdb_unique = (unique or {}).get('tvdb') if isinstance(unique, dict) else None
            if tvdb_unique:
                try:
                    if int(tvdb_unique) > 0:
                        ids['tvdb_id'] = str(tvdb_unique)
                except (ValueError, TypeError):
                    pass

        imdbnumber = pick.get('imdbnumber')
        if imdbnumber and str(imdbnumber).startswith('tt') and not ids.get('imdb_id'):
            ids['imdb_id'] = str(imdbnumber)

    def _ids_from_jsonrpc(self, ids: Dict[str, Any]) -> None:
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

    def _ids_from_infotag(self, ids: Dict[str, Any]) -> None:
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

        # TVDB is the API's identity, so the id is worth collecting even when a
        # TMDB one exists. On an episode tag `tvdb` is the episode record and the
        # series id lives on the show (tvdb_show / tvdbshow) — the two are told
        # apart by the media type, and get_media_ids drops the episode id when a
        # scraper repeated the series id on it.
        try:
            media_type = tag.getMediaType()
        except Exception:
            media_type = None

        try:
            tvdb = tag.getUniqueID('tvdb')
            if tvdb and not str(tvdb).startswith('tt'):
                val = str(tvdb)
                if int(val) > 0:
                    if media_type == 'movie':
                        if not ids.get('tvdb_id'):
                            ids['tvdb_id'] = val
                    elif not ids.get('tvdb_episode_id'):
                        ids['tvdb_episode_id'] = val
        except Exception:
            pass

        if not ids.get('tvdb_id'):
            for key in ('tvdb_show', 'tvdbshow'):
                try:
                    tvdb_show = tag.getUniqueID(key)
                except Exception:
                    tvdb_show = None
                if not tvdb_show:
                    continue
                try:
                    if int(str(tvdb_show)) > 0:
                        ids['tvdb_id'] = str(tvdb_show)
                        break
                except (ValueError, TypeError):
                    continue

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
