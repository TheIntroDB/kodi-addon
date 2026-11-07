# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 TheIntroDB
#
"""Unit tests for reading the settings the user just saved.

The bug these pin down: Kodi reads an add-on's settings once and caches them on the
add-on object, and `xbmcaddon.Addon(id)` returns that same cached object — so
`getSetting()` (stubbed here by `kodi_stubs.SETTINGS`) keeps answering with the
values from when the add-on loaded. Every symptom that followed — "no API key"
until a restart, no report button, no submit prompt — was a setting the service
could not see. The dialog's own file is the fresh source.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugin.video.tidb'))

import kodi_stubs  # noqa: E402

import addon_settings  # noqa: E402


class SavedSettingsTests(unittest.TestCase):
    def setUp(self):
        kodi_stubs.remove_settings()
        kodi_stubs.SETTINGS.clear()

    def tearDown(self):
        kodi_stubs.remove_settings()
        kodi_stubs.SETTINGS.clear()

    def test_a_setting_saved_after_load_is_seen(self):
        # The add-on's cached answer is empty; the dialog has since saved a key.
        kodi_stubs.SETTINGS['introdb_api_key'] = ''
        kodi_stubs.write_settings({'introdb_api_key': 'theintrodb:user_1:secret'})

        self.assertEqual('theintrodb:user_1:secret', addon_settings.setting('introdb_api_key'))
        # ... and getSetting still answers with the load-time value, which is the
        # behaviour the fix works around.
        self.assertEqual('', kodi_stubs.Addon().getSetting('introdb_api_key'))

    def test_a_later_save_is_seen_too(self):
        kodi_stubs.write_settings({'introdb_api_key': 'first'})
        self.assertEqual('first', addon_settings.setting('introdb_api_key'))

        kodi_stubs.write_settings({'introdb_api_key': 'second'}, keep_existing=True)
        self.assertEqual('second', addon_settings.setting('introdb_api_key'))

    def test_booleans_come_from_the_saved_file(self):
        kodi_stubs.SETTINGS['enable_submissions'] = 'false'
        kodi_stubs.write_settings({'enable_submissions': 'true'})

        self.assertTrue(addon_settings.setting_bool('enable_submissions'))
        # A setting the file does not carry keeps the add-on's answer (here: none,
        # so the default applies).
        self.assertFalse(addon_settings.setting_bool('never_saved'))
        self.assertTrue(addon_settings.setting_bool('never_saved', True))

    def test_a_missing_file_falls_back_to_the_addon(self):
        kodi_stubs.SETTINGS['introdb_api_key'] = 'from-get-setting'
        self.assertFalse(os.path.exists(kodi_stubs.SETTINGS_FILE))

        self.assertEqual('from-get-setting', addon_settings.setting('introdb_api_key'))
        self.assertEqual('fallback', addon_settings.setting('missing_key', 'fallback'))

    def test_a_key_the_file_does_not_carry_falls_back(self):
        kodi_stubs.SETTINGS['skip_offset'] = '9'
        kodi_stubs.write_settings({'introdb_api_key': 'saved'})

        self.assertEqual('9', addon_settings.setting('skip_offset'))

    def test_an_unreadable_file_falls_back_rather_than_raising(self):
        kodi_stubs.SETTINGS['introdb_api_key'] = 'from-get-setting'
        os.makedirs(kodi_stubs.PROFILE_PATH, exist_ok=True)
        with open(kodi_stubs.SETTINGS_FILE, 'w', encoding='utf-8') as handle:
            handle.write('<settings><setting id="broken"')

        self.assertEqual('from-get-setting', addon_settings.setting('introdb_api_key'))


if __name__ == '__main__':
    unittest.main()
