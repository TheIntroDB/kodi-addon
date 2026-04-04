# http client for theintrodb v2 /media — url from tmdb or imdb plus season/episode when needed
import json
import time
import xbmc
import xbmcaddon

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import Request, urlopen, HTTPError, URLError

ADDON = xbmcaddon.Addon()
_ADDON_ID = ADDON.getAddonInfo('id')

API_BASE = 'https://api.theintrodb.org/v2'
MIN_REQUEST_GAP = 0.4  # small gap between requests
_last_request_time = 0.0
_rate_limit_until = 0.0


def _debug_logging():
    return ADDON.getSetting('debug_logging') == 'true'


def _log_resp(body):
    if not _debug_logging():
        return
    snippet = body[:500] if len(body) > 500 else body
    xbmc.log('[IntroSkip] TheIntroDB response: {}'.format(snippet), xbmc.LOGINFO)


def _get_api_key():
    return (ADDON.getSetting('introdb_api_key') or '').strip()


def _is_enabled():
    try:
        return xbmcaddon.Addon(_ADDON_ID).getSetting('introdb_enabled') == 'true'
    except Exception:
        return ADDON.getSetting('introdb_enabled') == 'true'


def _wait_rate_limit():
    global _last_request_time
    now = time.time()
    if now < _rate_limit_until:
        xbmc.log('[IntroSkip] TheIntroDB rate-limited until {:.0f}'.format(
            _rate_limit_until), xbmc.LOGINFO)
        return False
    gap = now - _last_request_time
    if gap < MIN_REQUEST_GAP:
        time.sleep(MIN_REQUEST_GAP - gap)
    _last_request_time = time.time()
    return True


def _do_request(url, api_key):
    global _rate_limit_until
    req = Request(url)
    req.add_header('Accept', 'application/json')
    req.add_header('User-Agent', 'KodiSmartIntroSkip/1.0')
    if api_key:
        req.add_header('Authorization', 'Bearer {}'.format(api_key))

    try:
        resp = urlopen(req, timeout=8)
        body = resp.read().decode('utf-8')
        data = json.loads(body)
        _log_resp(body)
        return data
    except HTTPError as e:
        if e.code == 429:
            retry = 300
            for header in ('X-UsageLimit-Reset', 'X-RateLimit-Reset', 'Retry-After'):
                val = e.headers.get(header)
                if val:
                    try:
                        retry = int(val)
                    except ValueError:
                        pass
                    break
            _rate_limit_until = time.time() + retry
            xbmc.log('[IntroSkip] TheIntroDB 429 rate limited for {}s'.format(retry),
                     xbmc.LOGWARNING)
        elif e.code == 404:
            xbmc.log('[IntroSkip] TheIntroDB 404: not in database', xbmc.LOGINFO)
        else:
            xbmc.log('[IntroSkip] TheIntroDB HTTP {}'.format(e.code), xbmc.LOGWARNING)
        return None
    except URLError as e:
        xbmc.log('[IntroSkip] TheIntroDB network error: {}'.format(e.reason),
                 xbmc.LOGWARNING)
        return None
    except Exception as e:
        xbmc.log('[IntroSkip] TheIntroDB request failed: {}'.format(e),
                 xbmc.LOGERROR)
        return None


def _pick_best_segment(segments):
    # intro array may have multiple rows — take best score
    if not segments:
        return None, None

    best = None
    best_score = -1.0
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        start = seg.get('start_ms')
        end = seg.get('end_ms')
        if start is None:
            start = 0
        if end is None:
            continue
        if end <= start:
            continue
        conf = seg.get('confidence') if seg.get('confidence') is not None else 0.5
        count = seg.get('submission_count', 1)
        score = float(conf) + count * 0.001
        if score > best_score:
            best_score = score
            best = (start, end)

    if best:
        return best[0] / 1000.0, best[1] / 1000.0
    return None, None


def _normalize_imdb(imdb_id):
    if not imdb_id:
        return None
    s = str(imdb_id).strip()
    if not s.startswith('tt'):
        return None
    return s


def _valid_tmdb(tmdb_id):
    try:
        return int(str(tmdb_id)) > 0
    except (ValueError, TypeError):
        return False


def _episode_nums(season, episode):
    try:
        s = int(season)
        e = int(episode)
        return s, e
    except (TypeError, ValueError):
        return None, None


def _build_url(tmdb_id, imdb_id, season, episode, is_movie):
    # prefer tmdb; if missing use imdb (api matches show/episode)
    if tmdb_id and _valid_tmdb(tmdb_id):
        tid = str(tmdb_id).strip()
        if is_movie:
            return '{}/media?tmdb_id={}'.format(API_BASE, tid), 'tmdb'
        s, e = _episode_nums(season, episode)
        if s is None or e is None or s <= 0 or e <= 0:
            return None, None
        return (
            '{}/media?tmdb_id={}&season={}&episode={}'.format(API_BASE, tid, s, e),
            'tmdb',
        )

    imdb = _normalize_imdb(imdb_id)
    if not imdb:
        return None, None

    if is_movie:
        return '{}/media?imdb_id={}'.format(API_BASE, imdb), 'imdb'

    s, e = _episode_nums(season, episode)
    if s is None or e is None or s <= 0 or e <= 0:
        return None, None
    return '{}/media?imdb_id={}&season={}&episode={}'.format(
        API_BASE, imdb, s, e), 'imdb'


def query_intro(tmdb_id=None, imdb_id=None, season=None, episode=None, is_movie=False):
    # returns intro start/end in seconds, or none
    if not _is_enabled():
        return None, None

    url, mode = _build_url(tmdb_id, imdb_id, season, episode, is_movie)
    if not url:
        if tmdb_id or imdb_id:
            xbmc.log(
                '[IntroSkip] TheIntroDB: need TMDB id, or IMDb tt… id with season/episode for TV',
                xbmc.LOGINFO,
            )
        else:
            xbmc.log('[IntroSkip] TheIntroDB: no TMDB or IMDb id', xbmc.LOGINFO)
        return None, None

    xbmc.log('[IntroSkip] TheIntroDB query ({}): {}'.format(mode, url), xbmc.LOGINFO)

    if not _wait_rate_limit():
        return None, None

    api_key = _get_api_key()
    data = _do_request(url, api_key)
    if not data:
        return None, None

    if 'error' in data:
        xbmc.log('[IntroSkip] TheIntroDB error: {}'.format(data['error']), xbmc.LOGINFO)
        return None, None

    intro_start, intro_end = _pick_best_segment(data.get('intro', []))
    if intro_start is not None:
        xbmc.log('[IntroSkip] TheIntroDB intro: {:.1f}s -> {:.1f}s'.format(
            intro_start, intro_end), xbmc.LOGINFO)
    else:
        xbmc.log('[IntroSkip] TheIntroDB: no usable intro segment', xbmc.LOGINFO)

    return intro_start, intro_end
