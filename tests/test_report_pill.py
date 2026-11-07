# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Unit tests for the report control the skip prompt draws.

Kodi cannot run here, so what is pinned instead is the contract between the XML
both resolutions ship and the Python that drives it: the pill sits under the skip
pill and is drawn only while the window property overlay.py sets is non-empty, so
the mark-intro overlay that shares the file never draws it. The press handling is
covered too, where reporting must not skip and one segment must be reported once.
"""
import os
import sys
import threading
import time
import unittest
import xml.etree.ElementTree as ElementTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugin.video.tidb'))

import kodi_stubs  # noqa: E402

import overlay  # noqa: E402
import service  # noqa: E402
import submit_overlay  # noqa: E402

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOLUTIONS = ('1080i', '720p')
SKIP_BUTTON = 3001
REPORT_BUTTON = 3002
SKIP_IMAGES = (3003, 3004)


def _window(flag_callback=None, callback=None, monitor=None):
    return overlay.SkipOverlay(
        'overlay.xml', kodi_stubs.ADDON_PATH, 'default', '1080i',
        callback=callback, intro_end=None, player=None, monitor=monitor,
        segment_type='intro', segment_index=0, flag_callback=flag_callback)


def _wait_for(predicate, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _overlay_controls(resolution):
    path = os.path.join(
        REPO_DIR, 'plugin.video.tidb', 'resources', 'skins', 'default', resolution, 'overlay.xml')
    root = ElementTree.parse(path).getroot()
    group = root.find('controls/control')
    controls = {}
    for control in group.iter('control'):
        control_id = control.get('id')
        if control_id is None:
            continue
        controls[int(control_id)] = {
            'type': control.get('type'),
            'posx': int(control.findtext('posx')),
            'posy': int(control.findtext('posy')),
            'width': int(control.findtext('width')),
            'height': int(control.findtext('height')),
            'visible': (control.findtext('visible') or '').strip(),
        }
    return root, group, controls


class OverlayLayoutTests(unittest.TestCase):
    """What Kodi would draw, asserted on the XML, since no Kodi runs here."""

    def test_the_window_and_default_control_match_the_python_constants(self):
        for resolution in RESOLUTIONS:
            root, _group, _controls = _overlay_controls(resolution)
            self.assertEqual(str(overlay.OVERLAY_WINDOW_ID), root.get('id'), resolution)
            self.assertEqual(str(overlay.BUTTON_ID), root.findtext('defaultcontrol'), resolution)

    def test_both_resolutions_ship_the_same_controls(self):
        layouts = [_overlay_controls(resolution)[2] for resolution in RESOLUTIONS]
        self.assertEqual(set(layouts[0]), set(layouts[1]))
        self.assertIn(overlay.BUTTON_ID, layouts[0])
        self.assertIn(overlay.FLAG_BUTTON_ID, layouts[0])

    def test_the_report_pill_sits_under_the_skip_pill(self):
        for resolution in RESOLUTIONS:
            _root, group, controls = _overlay_controls(resolution)
            skip = controls[SKIP_BUTTON]
            report = controls[REPORT_BUTTON]
            self.assertEqual('button', report['type'], resolution)
            self.assertEqual(skip['posx'], report['posx'], resolution)
            self.assertEqual(skip['width'], report['width'], resolution)
            self.assertGreaterEqual(report['posy'], skip['posy'] + skip['height'], resolution)
            # Inside the group it lives in, so the pill is never clipped.
            self.assertLessEqual(
                report['posy'] + report['height'], int(group.findtext('height')), resolution)

    def test_the_report_pill_is_driven_by_the_window_property_the_addon_sets(self):
        # Kodi's Control.setVisible cannot show a control whose <visible> condition is
        # false — it only moves the force-hidden flag — so the pill's visibility is a
        # condition reading a window property. The mark-intro overlay shares this XML
        # and never sets that property, so it never draws the pill.
        expected = '!String.IsEmpty(Window.Property({}))'.format(overlay.REPORT_PROPERTY)
        for resolution in RESOLUTIONS:
            _root, _group, controls = _overlay_controls(resolution)
            self.assertEqual(expected, controls[REPORT_BUTTON]['visible'], resolution)
            for image_id in (overlay._BG_FLAG_SHADOW, overlay._BG_FLAG_FILL):
                self.assertEqual(expected, controls[image_id]['visible'], resolution)
            # The skip pill carries no condition: nothing hides it but its own code.
            self.assertEqual('', controls[SKIP_BUTTON]['visible'], resolution)
            for image_id in SKIP_IMAGES:
                self.assertEqual('', controls[image_id]['visible'], resolution)


class ReportPressTests(unittest.TestCase):
    def test_the_report_pill_is_offered_only_when_reporting_is_available(self):
        offered = _window(flag_callback=lambda: True)
        offered.onInit()
        self.assertEqual('1', offered.getProperty(overlay.REPORT_PROPERTY))
        self.assertEqual('string-32043', offered.getControl(overlay.FLAG_BUTTON_ID).label)
        for image_id in (overlay._BG_FLAG_SHADOW, overlay._BG_FLAG_FILL):
            self.assertIsNotNone(offered.getControl(image_id).image)

        plain = _window()
        plain.onInit()
        self.assertEqual('', plain.getProperty(overlay.REPORT_PROPERTY))

        # Neither prompt drives the pill with setVisible: Kodi ignores it for a
        # control whose <visible> condition is false, which is the bug this shape
        # exists to avoid.
        for window in (offered, plain):
            for control_id in (overlay.FLAG_BUTTON_ID, overlay._BG_FLAG_SHADOW, overlay._BG_FLAG_FILL):
                self.assertEqual([], window.getControl(control_id).set_visible_calls)

    def test_the_mark_overlay_never_offers_the_report_pill(self):
        # The mark-intro pill reuses overlay.xml, so it must leave the property the
        # report pill's condition reads unset, and draw no pill of its own.
        class _AbortingMonitor(kodi_stubs.Monitor):
            def waitForAbort(self, timeout=None):
                return True

        wnd = submit_overlay.SubmitMarkOverlay(
            'overlay.xml', kodi_stubs.ADDON_PATH, 'default', '1080i',
            label_text='Mark Intro Start', player=None, monitor=_AbortingMonitor())
        wnd.onInit()

        self.assertEqual('', wnd.getProperty(overlay.REPORT_PROPERTY))
        self.assertEqual([], wnd.getControl(overlay.FLAG_BUTTON_ID).set_visible_calls)

    def test_pressing_report_reports_and_leaves_the_pill_open(self):
        calls = []
        reported = threading.Event()

        def flag():
            calls.append(1)
            reported.set()
            return True

        skipped = []
        wnd = _window(flag_callback=flag, callback=lambda: skipped.append(1))
        wnd.onClick(overlay.FLAG_BUTTON_ID)

        self.assertTrue(reported.wait(2.0))
        self.assertEqual(1, len(calls))
        # Reporting a bad segment and skipping it are separate decisions, so the
        # skip pill is still on offer while the report is in flight.
        self.assertEqual([], skipped)
        self.assertFalse(wnd.skip_pressed)
        self.assertFalse(wnd._closed)

    def test_a_select_action_reports_when_the_report_pill_has_focus(self):
        reported = threading.Event()
        wnd = _window(flag_callback=lambda: (reported.set(), True)[1])
        wnd.setFocusId(overlay.FLAG_BUTTON_ID)
        wnd.onAction(kodi_stubs.Action(overlay.ACTION_SELECT))
        self.assertTrue(reported.wait(2.0))

    def test_one_press_reports_a_segment_once(self):
        # Kodi can deliver one OK press as both a click and a select action, and
        # TheIntroDB keys one vote per account per media.
        calls = []
        wnd = _window(flag_callback=lambda: (calls.append(1), True)[1])
        wnd.onClick(overlay.FLAG_BUTTON_ID)
        self.assertTrue(_wait_for(lambda: wnd._flag_reported))

        wnd.onClick(overlay.FLAG_BUTTON_ID)
        self.assertEqual(1, len(calls))

    def test_a_failed_report_can_be_tried_again(self):
        calls = []
        wnd = _window(flag_callback=lambda: (calls.append(1), False)[1])
        wnd.onClick(overlay.FLAG_BUTTON_ID)
        self.assertTrue(_wait_for(lambda: len(calls) == 1))
        self.assertTrue(_wait_for(lambda: not wnd._flag_in_flight))

        wnd.onClick(overlay.FLAG_BUTTON_ID)
        self.assertTrue(_wait_for(lambda: len(calls) == 2))

    def test_the_skip_pill_still_skips_and_closes(self):
        skipped = []
        wnd = _window(callback=lambda: skipped.append(1), flag_callback=lambda: True)
        wnd.onClick(overlay.BUTTON_ID)
        self.assertEqual([1], skipped)
        self.assertTrue(wnd.skip_pressed)
        self.assertTrue(wnd._closed)


class ReportServiceTests(unittest.TestCase):
    """The service turns a press into the vote, and a toast for the viewer."""

    def setUp(self):
        self._original_flag = service.introdb.flag_media
        self._original_reporter = service.REPORTER
        service.REPORTER = None
        del kodi_stubs.EXECUTED_BUILTINS[:]
        self.reports = []

    def tearDown(self):
        service.introdb.flag_media = self._original_flag
        service.REPORTER = self._original_reporter
        kodi_stubs.SETTINGS.pop('enable_report_button', None)
        kodi_stubs.SETTINGS.pop('introdb_api_key', None)

    def _session(self, media_ids):
        session = service.PlaybackSession()
        session.media_ids = media_ids
        return session

    def test_reporting_needs_the_setting_and_a_key(self):
        # The vote is the account's, so the pill is not offered without a key.
        kodi_stubs.SETTINGS['enable_report_button'] = 'true'
        self.assertFalse(service._report_enabled())

        kodi_stubs.SETTINGS['introdb_api_key'] = 'theintrodb:user_1:secret'
        self.assertTrue(service._report_enabled())

        kodi_stubs.SETTINGS['enable_report_button'] = 'false'
        self.assertFalse(service._report_enabled())

    def test_a_report_carries_the_playing_item_and_toasts_without_commas(self):
        def fake_flag_media(**kwargs):
            self.reports.append(kwargs)
            return True, 'One of tvdb_id, tmdb_id or imdb_id is required'

        service.introdb.flag_media = fake_flag_media
        session = self._session({
            'tvdb_id': '73871', 'tmdb_id': None, 'imdb_id': None,
            'season': 7, 'episode': 1, 'is_movie': False,
        })

        self.assertTrue(service._report_segment(session))
        self.assertEqual(1, len(self.reports))
        self.assertEqual('73871', self.reports[0]['tvdb_id'])
        self.assertEqual(7, self.reports[0]['season'])
        self.assertEqual(1, self.reports[0]['episode'])
        self.assertFalse(self.reports[0]['is_movie'])

        toast = kodi_stubs.EXECUTED_BUILTINS[-1]
        self.assertTrue(toast.startswith('Notification(TheIntroDB, '), toast)
        # Only the two separators: the message's own commas would be read as more
        # arguments by the builtin.
        self.assertEqual(2, toast.count(','))

    def test_a_report_without_media_ids_asks_nothing(self):
        def fake_flag_media(**kwargs):
            self.reports.append(kwargs)
            return True, 'reported'

        service.introdb.flag_media = fake_flag_media
        self.assertFalse(service._report_segment(self._session(None)))
        self.assertEqual([], self.reports)
        self.assertEqual([], kodi_stubs.EXECUTED_BUILTINS)


if __name__ == '__main__':
    unittest.main()
