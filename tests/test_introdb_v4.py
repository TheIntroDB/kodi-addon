# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Unit tests for the API client's v4 request shape.

Kodi's Python modules don't exist off-device, so the shared stubs in
`kodi_stubs` are imported (and installed) before the addon module is.
"""
import json
import os
import sys
import time
import unittest
from email.message import Message

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugin.video.tidb'))

import kodi_stubs  # noqa: E402

_SETTINGS = kodi_stubs.SETTINGS

import introdb  # noqa: E402

_SETTINGS['introdb_enabled'] = 'true'


def _headers(**values):
    message = Message()
    for key, value in values.items():
        message[key.replace('_', '-')] = str(value)
    return message


class _HttpError(introdb.HTTPError):
    def __init__(self, code, headers, body=''):
        super().__init__('http://example.invalid', code, 'error', headers, None)
        self._body = body

    def read(self):
        return self._body.encode('utf-8')


class _FakeResponse:
    """What urlopen hands back on success: only read() is used."""

    def __init__(self, body='', status=200):
        self._body = body
        self.status = status

    def read(self):
        return self._body.encode('utf-8')

    def getcode(self):
        return self.status


class ApiVersionTests(unittest.TestCase):
    def test_client_speaks_v4(self):
        self.assertEqual('v4', introdb.API_VERSION)
        self.assertEqual('https://api.theintrodb.org/v4', introdb.API_BASE)


class UrlBuildingTests(unittest.TestCase):
    def test_tvdb_is_preferred_and_carries_order_and_episode_id(self):
        url, mode = introdb._build_url(
            tvdb_id=73871, tmdb_id=615, imdb_id='tt0149460',
            season=7, episode=1, is_movie=False,
            duration_ms=1297000, mapping='alternate', tvdb_episode_id=1051911)
        self.assertEqual('tvdb', mode)
        self.assertEqual(
            'https://api.theintrodb.org/v4/media?tvdb_id=73871&season=7&episode=1'
            '&mapping=alternate&tvdb_episode_id=1051911&duration_ms=1297000',
            url)

    def test_tmdb_request_drops_order_and_episode_id(self):
        # A tmdb_id request is always read as TMDB numbering, so an order beside it
        # would be a lie rather than a hint.
        url, mode = introdb._build_url(
            tmdb_id=615, season=7, episode=1, mapping='alternate', tvdb_episode_id=1051911)
        self.assertEqual('tmdb', mode)
        self.assertEqual('https://api.theintrodb.org/v4/media?tmdb_id=615&season=7&episode=1', url)

    def test_movie_urls_and_imdb_fallback(self):
        self.assertEqual(
            ('https://api.theintrodb.org/v4/media?tvdb_id=169', 'tvdb'),
            introdb._build_url(tvdb_id=169, is_movie=True))
        self.assertEqual(
            ('https://api.theintrodb.org/v4/media?imdb_id=tt0111161', 'imdb'),
            introdb._build_url(imdb_id='tt0111161', is_movie=True))

    def test_tv_request_needs_a_usable_episode_number(self):
        self.assertEqual((None, None), introdb._build_url(tmdb_id=615, season=0, episode=0))

    def test_candidates_fall_back_to_the_next_identity(self):
        candidates = introdb._media_url_candidates(
            tvdb_id=73871, tmdb_id=615, imdb_id='tt0149460', season=7, episode=1,
            is_movie=False, duration_ms=None, mapping='alternate', tvdb_episode_id=1051911)
        self.assertEqual([
            'https://api.theintrodb.org/v4/media?tvdb_id=73871&season=7&episode=1&mapping=alternate&tvdb_episode_id=1051911',
            'https://api.theintrodb.org/v4/media?tvdb_id=73871&season=7&episode=1&mapping=alternate',
            'https://api.theintrodb.org/v4/media?tmdb_id=615&season=7&episode=1',
            'https://api.theintrodb.org/v4/media?imdb_id=tt0149460&season=7&episode=1',
        ], [url for url, _mode in candidates])


class QueryFallbackTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._original_request = introdb._do_request
        self._original_wait = introdb._wait_rate_limit
        introdb._wait_rate_limit = lambda: True

    def tearDown(self):
        introdb._do_request = self._original_request
        introdb._wait_rate_limit = self._original_wait

    def _responder(self, statuses):
        def fake(url, api_key):
            self.calls.append(url)
            status = statuses.pop(0)
            if status == 'ok':
                return 'ok', {'intro': [{'start_ms': None, 'end_ms': 29344}]}
            return status, None
        introdb._do_request = fake

    def test_404_moves_on_to_the_next_identity(self):
        self._responder(['not_found', 'ok'])
        data, mode = introdb._query_media(tvdb_id=73871, tmdb_id=615, season=7, episode=1)
        # The tvdb addressing found nothing, so the same episode was asked for by
        # tmdb_id — the id a stream's metadata usually carries.
        self.assertEqual('tmdb', mode)
        self.assertIsNotNone(data)
        self.assertEqual(2, len(self.calls))
        self.assertIn('tvdb_id=73871', self.calls[0])
        self.assertIn('tmdb_id=615', self.calls[1])

    def test_rate_limit_stops_the_fallback_chain(self):
        self._responder(['rate_limited'])
        data, mode = introdb._query_media(tvdb_id=73871, tmdb_id=615, season=7, episode=1)
        self.assertIsNone(data)
        self.assertIsNone(mode)
        self.assertEqual(1, len(self.calls))

    def test_every_identity_missing_returns_nothing(self):
        self._responder(['not_found', 'not_found', 'not_found'])
        data, mode = introdb._query_media(tvdb_id=73871, tmdb_id=615, imdb_id='tt0149460', season=7, episode=1)
        self.assertIsNone(data)
        self.assertIsNone(mode)
        self.assertEqual(3, len(self.calls))


class RetryAfterTests(unittest.TestCase):
    def test_retry_after_header_is_preferred(self):
        error = _HttpError(429, _headers(Retry_After=10, X_RateLimit_Reset=999999))
        self.assertEqual(10, introdb._retry_after_seconds(error, ''))

    def test_rate_limit_reset_is_clamped_to_the_burst_window(self):
        error = _HttpError(429, _headers(X_RateLimit_Reset=999999))
        self.assertEqual(introdb.RATE_RESET_CLAMP, introdb._retry_after_seconds(error, ''))

    def test_usage_limit_reset_is_trusted_up_to_the_daily_ceiling(self):
        body = json.dumps({'error': 'Usage limit exceeded', 'code': 'usage_limit_exceeded'})
        error = _HttpError(429, _headers(X_UsageLimit_Reset=49000), body)
        self.assertEqual(49000, introdb._retry_after_seconds(error, body))

        error = _HttpError(429, _headers(X_UsageLimit_Reset=999999), body)
        self.assertEqual(introdb.USAGE_RESET_CLAMP, introdb._retry_after_seconds(error, body))

    def test_specific_media_usage_limit_is_recognized_by_its_code(self):
        body = json.dumps({'error': 'Usage limit exceeded', 'code': 'specific_media_usage_limit_exceeded'})
        error = _HttpError(429, _headers(Retry_After=7200), body)
        self.assertEqual(7200, introdb._retry_after_seconds(error, body))


class ApiKeyProbeTests(unittest.TestCase):
    def setUp(self):
        self._original = introdb.urlopen
        self.urls = []

    def tearDown(self):
        introdb.urlopen = self._original
        _SETTINGS.pop('introdb_api_key', None)

    def test_probe_targets_user_stats(self):
        def fake(request, timeout=None):
            self.urls.append(request.full_url)
            raise _HttpError(401, _headers())

        introdb.urlopen = fake
        _SETTINGS['introdb_api_key'] = 'theintrodb:user_1:secret'
        valid, message = introdb.test_api_key()
        self.assertFalse(valid)
        self.assertIn('401', message)
        self.assertEqual(['https://api.theintrodb.org/v4/user/stats'], self.urls)

    def test_probe_reports_an_unexpected_status_instead_of_passing(self):
        def fake(request, timeout=None):
            raise _HttpError(404, _headers())

        introdb.urlopen = fake
        _SETTINGS['introdb_api_key'] = 'theintrodb:user_1:secret'
        valid, message = introdb.test_api_key()
        self.assertFalse(valid)
        self.assertIn('404', message)


class Submit429Tests(unittest.TestCase):
    """A submission's 429 shares the lookup budget, so it must be bounded too."""

    def setUp(self):
        self._original_urlopen = introdb.urlopen
        self._original_wait = introdb._wait_rate_limit
        introdb._wait_rate_limit = lambda: True
        introdb._rate_limit_until = 0.0
        _SETTINGS['introdb_api_key'] = 'theintrodb:user_1:secret'

    def tearDown(self):
        introdb.urlopen = self._original_urlopen
        introdb._wait_rate_limit = self._original_wait
        introdb._rate_limit_until = 0.0
        _SETTINGS.pop('introdb_api_key', None)

    def _submit(self, headers, body=''):
        def fake(request, timeout=None):
            raise _HttpError(429, headers, body)

        introdb.urlopen = fake
        ok, _message = introdb.submit_segment(
            tvdb_id=169, is_movie=True, segment='intro', start_sec=30, end_sec=90)
        self.assertFalse(ok)
        return introdb._rate_limit_until - time.time()

    def test_daily_budget_reset_is_trusted(self):
        body = json.dumps({'error': 'Usage limit exceeded', 'code': 'usage_limit_exceeded'})
        remaining = self._submit(_headers(X_UsageLimit_Reset=49000, Retry_After=49000), body)
        self.assertGreater(remaining, 48000)
        self.assertLess(remaining, 49001)

    def test_burst_reset_is_clamped_and_never_lands_in_the_past(self):
        remaining = self._submit(_headers(X_RateLimit_Reset=999999))
        self.assertGreater(remaining, 0)
        self.assertLessEqual(remaining, introdb.RATE_RESET_CLAMP)


class FlagMediaTests(unittest.TestCase):
    """A report is the account's own vote, so the request carries the key and the
    addressing the lookup for the same item used."""

    def setUp(self):
        self._original_urlopen = introdb.urlopen
        self._original_wait = introdb._wait_rate_limit
        introdb._wait_rate_limit = lambda: True
        introdb._rate_limit_until = 0.0
        _SETTINGS['introdb_api_key'] = 'theintrodb:user_1:secret'
        self.requests = []

    def tearDown(self):
        introdb.urlopen = self._original_urlopen
        introdb._wait_rate_limit = self._original_wait
        introdb._rate_limit_until = 0.0
        _SETTINGS.pop('introdb_api_key', None)

    def _respond(self, body='{"message":"Media flagged successfully"}', status=200, headers=None):
        def fake(request, timeout=None):
            self.requests.append(request)
            if status >= 400:
                raise _HttpError(status, headers or _headers(), body)
            return _FakeResponse(body, status)
        introdb.urlopen = fake

    def _sent(self):
        request = self.requests[-1]
        return request.full_url, request.headers, json.loads(request.data.decode('utf-8'))

    def test_a_report_carries_the_key_and_the_lookup_addressing(self):
        self._respond()
        accepted, message = introdb.flag_media(tvdb_id=73871, season=7, episode=1)
        self.assertTrue(accepted)
        self.assertEqual('Media flagged successfully', message)

        url, headers, body = self._sent()
        self.assertEqual('https://api.theintrodb.org/v4/flag-vote', url)
        self.assertEqual('POST', self.requests[-1].get_method())
        self.assertEqual('application/json', headers.get('Content-type'))
        self.assertEqual('Bearer theintrodb:user_1:secret', headers.get('Authorization'))
        # The id the lookup asked with, and the numbers in that id's own order.
        self.assertEqual({'tvdb_id': 73871, 'type': 'tv', 'season': 7, 'episode': 1}, body)

    def test_a_movie_report_omits_the_episode_coordinates(self):
        self._respond()
        accepted, _message = introdb.flag_media(tvdb_id=169, is_movie=True)
        self.assertTrue(accepted)
        self.assertEqual({'tvdb_id': 169, 'type': 'movie'}, self._sent()[2])

    def test_a_report_falls_back_to_tmdb_then_imdb(self):
        self._respond()
        introdb.flag_media(tmdb_id=1297842, is_movie=True)
        self.assertEqual({'tmdb_id': 1297842, 'type': 'movie'}, self._sent()[2])
        introdb.flag_media(imdb_id='tt27613895', is_movie=True)
        self.assertEqual({'imdb_id': 'tt27613895', 'type': 'movie'}, self._sent()[2])

    def test_a_report_needs_a_key_and_an_identifier(self):
        _SETTINGS.pop('introdb_api_key')
        accepted, message = introdb.flag_media(tvdb_id=73871, season=1, episode=1)
        self.assertFalse(accepted)
        self.assertIn('API key', message)

        _SETTINGS['introdb_api_key'] = 'theintrodb:user_1:secret'
        accepted, message = introdb.flag_media(season=1, episode=1)
        self.assertFalse(accepted)
        self.assertIn('TVDB, TMDB or IMDb', message)

    def test_an_episode_report_needs_usable_numbers(self):
        # The API reads the numbers in the identified id's order, so a report
        # without them cannot name an episode; it is refused before the request.
        self._respond()
        accepted, message = introdb.flag_media(tvdb_id=73871)
        self.assertFalse(accepted)
        self.assertIn('Season and episode', message)
        self.assertEqual([], self.requests)

    def test_a_paused_budget_skips_the_request(self):
        introdb._wait_rate_limit = lambda: False
        accepted, message = introdb.flag_media(tvdb_id=73871, season=1, episode=1)
        self.assertFalse(accepted)
        self.assertIn('Rate limited', message)
        self.assertEqual([], self.requests)

    def test_a_repeat_report_is_a_settled_outcome(self):
        # One vote per account per media: the segment is already known about,
        # which is the outcome the viewer wanted.
        self._respond(body='{"error":"You have already voted to flag this media"}', status=409)
        accepted, message = introdb.flag_media(tvdb_id=73871, season=1, episode=1)
        self.assertTrue(accepted)
        self.assertIn('Already reported', message)

    def test_a_refusal_is_reported_with_the_api_message(self):
        self._respond(body='{"error":"Invalid API key"}', status=401)
        accepted, message = introdb.flag_media(tvdb_id=73871, season=1, episode=1)
        self.assertFalse(accepted)
        self.assertEqual('Invalid API key', message)

    def test_a_rate_limit_pauses_the_budget_the_lookups_share(self):
        self._respond(body='{"error":"Rate limit exceeded"}', status=429,
                      headers=_headers(Retry_After=30))
        accepted, _message = introdb.flag_media(tvdb_id=73871, season=1, episode=1)
        self.assertFalse(accepted)
        remaining = introdb._rate_limit_until - time.time()
        self.assertGreater(remaining, 25)
        self.assertLessEqual(remaining, 30)


if __name__ == '__main__':
    unittest.main()
