# kodi service entry: poll playback, query theintrodb, show skip ui or auto-seek
import xbmc
import xbmcaddon

from player import TIDBPlayer
import skipper
import overlay as overlay_mod
import introdb

ADDON = xbmcaddon.Addon()
_ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

# String IDs for localization
STR_SKIP_INTRO = 32001
STR_SKIP_RECAP = 32003
STR_SKIP_CREDITS = 32004
STR_SKIP_PREVIEW = 32005


class TIDBMonitor(xbmc.Monitor):
    pass


def _debug_osd(message):
    # optional toast spam for debugging
    if ADDON.getSetting('debug_osd') == 'true':
        xbmc.executebuiltin('Notification(TIDB, {}, 1500)'.format(message))


def _fresh_bool(key):
    # read setting again from disk so gui changes apply without restart
    try:
        return xbmcaddon.Addon(_ADDON_ID).getSetting(key) == 'true'
    except Exception:
        return ADDON.getSetting(key) == 'true'


def _run_service():
    monitor = TIDBMonitor()
    player = TIDBPlayer()

    xbmc.log('[TheIntroDB] Service started', xbmc.LOGINFO)

    current_file = None
    cached_media_ids = None
    cached_all_segments = None
    processed_segments = {}
    next_episode_info = None
    next_episode_checked = False

    while not monitor.abortRequested():
        if monitor.waitForAbort(1.0):
            break

        if not player.playback_started:
            current_file = None
            cached_media_ids = None
            cached_all_segments = None
            processed_segments.clear()
            next_episode_info = None
            next_episode_checked = False
            continue

        # skip movies that do not look like tv; player decides
        if not player.is_tv_content:
            continue

        filename = player.filename
        if not filename:
            continue

        if filename != current_file:
            current_file = filename
            cached_media_ids = None
            cached_all_segments = None
            processed_segments.clear()
            next_episode_info = None
            next_episode_checked = False
            xbmc.log('[TheIntroDB] Reset segment tracking for file: {}'.format(filename), xbmc.LOGINFO)

        _debug_osd('Monitoring: {}'.format(filename[-40:]))

        introdb_on = _fresh_bool('introdb_enabled')
        auto_skip = _fresh_bool('auto_skip')

        if ADDON.getSetting('debug_logging') == 'true':
            _raw = xbmcaddon.Addon(_ADDON_ID).getSetting('introdb_enabled')
            xbmc.log(
                '[TheIntroDB] introdb_enabled raw={!r} lookups_on={}'.format(_raw, introdb_on),
                xbmc.LOGINFO,
            )

        if cached_media_ids is None:
            cached_media_ids = player.get_media_ids()
        media_ids = cached_media_ids
        tmdb = media_ids.get('tmdb_id')
        imdb = media_ids.get('imdb_id')
        m_season = media_ids.get('season')
        m_episode = media_ids.get('episode')
        m_movie = media_ids.get('is_movie', False)

        xbmc.log('[TheIntroDB] Media IDs: tmdb={} imdb={} S{}E{} movie={}'.format(
            tmdb, imdb, m_season, m_episode, m_movie), xbmc.LOGINFO)
        _debug_osd('tmdb={} imdb={} S{}E{}'.format(
            tmdb or '-', imdb or '-', m_season or '?', m_episode or '?'))

        all_segments = {}
        if introdb_on and (tmdb or imdb):
            if cached_all_segments is None:
                cached_all_segments = introdb.query_all_segments(
                    tmdb_id=tmdb,
                    imdb_id=imdb,
                    season=m_season,
                    episode=m_episode,
                    is_movie=m_movie,
                )
            all_segments = cached_all_segments or {}

        # Collect all enabled segments from all types and sort them chronologically
        all_enabled_segments = []
        
        # Debug: Log all available segments from API (only if debug logging is enabled)
        if all_segments and ADDON.getSetting('debug_logging') == 'true':
            xbmc.log('[TheIntroDB] API returned segments: {}'.format(list(all_segments.keys())), xbmc.LOGINFO)
            for seg_type, segs in all_segments.items():
                xbmc.log('[TheIntroDB] {} segments: {}'.format(seg_type, len(segs)), xbmc.LOGINFO)
        
        # Collect all enabled segments
        segment_priority = ['intro', 'recap', 'preview', 'credits']
        for segment_type in segment_priority:
            # Check if this segment type is enabled in settings
            setting_key = 'enable_{}'.format(segment_type)
            is_enabled = _fresh_bool(setting_key)
            
            if not is_enabled:
                continue
                
            if segment_type not in all_segments:
                continue
                
            segments = all_segments[segment_type]
            if not segments:
                continue
                
            # Add all segments from this type with their type info
            for segment_idx, segment in enumerate(segments):
                segment_with_type = segment.copy()
                segment_with_type['type'] = segment_type
                segment_with_type['index'] = segment_idx
                all_enabled_segments.append(segment_with_type)
        
        # Sort all segments by start time (chronological order)
        all_enabled_segments.sort(key=lambda x: x['start'] if x['start'] is not None else 0)
        
        # Log total enabled segments (only if debug logging is enabled)
        if ADDON.getSetting('debug_logging') == 'true':
            xbmc.log('[TheIntroDB] Total enabled segments to process: {}'.format(len(all_enabled_segments)), xbmc.LOGINFO)

        # Process segments in chronological order
        for segment_idx, segment in enumerate(all_enabled_segments):
            segment_type = segment['type']
            api_start = segment['start']
            api_end = segment['end']
            
            if ADDON.getSetting('debug_logging') == 'true':
                xbmc.log('[TheIntroDB] Processing {} segment {}: start={}, end={}'.format(segment_type, segment_idx, api_start, api_end), xbmc.LOGINFO)
            
            if api_start is None and api_end is None:
                continue
                
            # Handle segments with null start/end appropriately
            if api_start is None:
                api_start = 0
            
            # Credits/preview with a null end means "to the end of the episode".
            is_next_episode_candidate = (segment_type in ['credits', 'preview']) and (api_end is None)
            
            if api_end is None:
                # For credits/preview with null end, use total time
                try:
                    api_end = player.getTotalTime() - 10  # 10 seconds before end
                except:
                    continue
                    
            # Use segment type name without numbers
            segment_display_name = segment_type
            
            # Create unique key for this segment (type + index)
            segment_key = '{}_{}'.format(segment_type, segment_idx)
            
            msg = 'TheIntroDB {}: {:.1f}s -> {:.1f}s'.format(segment_display_name, api_start, api_end)
            xbmc.log('[TheIntroDB] {}'.format(msg), xbmc.LOGINFO)
            _debug_osd(msg)

            current_time = player.getTime() if player.isPlaying() else 0

            if ADDON.getSetting('debug_logging') == 'true':
                xbmc.log('[TheIntroDB] Checking timing for {} segment {}: current={:.1f}s, start={:.1f}s, end={:.1f}s'.format(segment_type, segment_idx, current_time, api_start, api_end), xbmc.LOGINFO)

            if not _should_show_segment_button(processed_segments, segment_key, current_time, api_start, api_end):
                if ADDON.getSetting('debug_logging') == 'true':
                    xbmc.log(
                        '[TheIntroDB] Skipping {} button - outside segment or already shown for this entry'.format(segment_display_name),
                        xbmc.LOGINFO,
                    )
                continue

            if not player.isPlaying():
                continue

            segment_names = {
                'intro': ADDON.getLocalizedString(STR_SKIP_INTRO),
                'recap': ADDON.getLocalizedString(STR_SKIP_RECAP),
                'credits': ADDON.getLocalizedString(STR_SKIP_CREDITS),
                'preview': ADDON.getLocalizedString(STR_SKIP_PREVIEW)
            }
            
            segment_type_for_overlay = segment_type
            segment_name = segment_names.get(segment_type, segment_type.title())
            is_next_episode_segment = False

            if is_next_episode_candidate:
                if not next_episode_checked:
                    next_episode_info = player.get_next_episode()
                    next_episode_checked = True
                if next_episode_info:
                    is_next_episode_segment = True
                    segment_type_for_overlay = 'next_episode'
                    segment_name = overlay_mod.ADDON.getLocalizedString(overlay_mod.STR_NEXT_EPISODE)
                    xbmc.log(
                        '[TheIntroDB] Showing Next Episode for end-of-media {} segment'.format(segment_type),
                        xbmc.LOGINFO,
                    )
            
            # Handle auto-skip logic: only auto-skip intro segments
            if auto_skip and segment_type == 'intro':
                skipper.execute_skip(player, api_start, api_end, filename, segment_type)
                _debug_osd('Auto-skipped {}'.format(segment_name))
                xbmc.log('[TheIntroDB] Auto-skipped {} to {:.1f}s'.format(segment_name, api_end), xbmc.LOGINFO)
            elif is_next_episode_segment:
                if monitor.abortRequested():
                    break
                xbmc.log('[TheIntroDB] Showing next episode overlay for {}'.format(segment_name), xbmc.LOGINFO)
                pressed = overlay_mod.show_skip_overlay(
                    intro_end=api_end,
                    player=player,
                    monitor=monitor,
                    segment_type=segment_type_for_overlay,
                    segment_index=segment_idx,
                )
                if pressed:
                    xbmc.log('[TheIntroDB] User pressed Next Episode', xbmc.LOGINFO)
                    was_opened = player.play_next_episode(next_episode_info)
                    if was_opened:
                        _debug_osd('Next Episode')
                    else:
                        xbmc.log('[TheIntroDB] Next episode was no longer available to open', xbmc.LOGWARNING)
                else:
                    xbmc.log('[TheIntroDB] User did NOT press Next Episode - continuing', xbmc.LOGINFO)
            elif auto_skip and segment_type != 'intro':
                # Auto-skip is enabled but this is not an intro segment - show skip button instead
                if monitor.abortRequested():
                    break
                xbmc.log('[TheIntroDB] Auto-skip enabled but showing button for non-intro segment: {}'.format(segment_name), xbmc.LOGINFO)
                pressed = overlay_mod.show_skip_overlay(
                    intro_end=api_end,
                    player=player,
                    monitor=monitor,
                    segment_type=segment_type_for_overlay,
                    segment_index=segment_idx,
                )
                if pressed:
                    xbmc.log('[TheIntroDB] User pressed Skip {}'.format(segment_name), xbmc.LOGINFO)
                    skipper.execute_skip(player, api_start, api_end, filename, segment_type)
                    _debug_osd('Skipped {} to {:.1f}s'.format(segment_name, api_end))
                else:
                    xbmc.log('[TheIntroDB] User did NOT skip {} - continuing to next segment'.format(segment_name), xbmc.LOGINFO)
            else:
                # Auto-skip is disabled - show skip button for all segments
                if monitor.abortRequested():
                    break
                xbmc.log('[TheIntroDB] Showing skip overlay for {}'.format(segment_name), xbmc.LOGINFO)
                pressed = overlay_mod.show_skip_overlay(
                    intro_end=api_end,
                    player=player,
                    monitor=monitor,
                    segment_type=segment_type_for_overlay,
                    segment_index=segment_idx,
                )
                if pressed:
                    xbmc.log('[TheIntroDB] User pressed Skip {}'.format(segment_name), xbmc.LOGINFO)
                    skipper.execute_skip(player, api_start, api_end, filename, segment_type)
                    _debug_osd('Skipped {} to {:.1f}s'.format(segment_name, api_end))
                else:
                    xbmc.log('[TheIntroDB] User did NOT skip {} - continuing to next segment'.format(segment_name), xbmc.LOGINFO)

    xbmc.log('[TheIntroDB] Service stopped', xbmc.LOGINFO)


def _should_show_segment_button(processed_segments, segment_key, current_time, segment_start, segment_end, margin=0.25):
    """
    Show the skip button once per segment entry.

    If playback exits a segment and later re-enters it, including by seeking into
    the middle of the segment, the next entry gets a fresh 5 second overlay.
    """
    state = processed_segments.setdefault(segment_key, {
        'inside': False,
        'shown_for_entry': False,
        'last_time': None,
    })

    inside_segment = segment_start <= current_time < (segment_end - margin)
    previous_time = state.get('last_time')

    if not inside_segment:
        state['inside'] = False
        state['shown_for_entry'] = False
        state['last_time'] = current_time
        return False

    reentered = (not state['inside'])
    if previous_time is not None and current_time + margin < previous_time:
        reentered = True

    if reentered:
        if ADDON.getSetting('debug_logging') == 'true':
            xbmc.log('[TheIntroDB] Entry detected for {} at {:.1f}s'.format(segment_key, current_time), xbmc.LOGINFO)
        state['shown_for_entry'] = False

    state['inside'] = True
    state['last_time'] = current_time

    if state['shown_for_entry']:
        return False

    state['shown_for_entry'] = True
    return True
if __name__ == '__main__':
    _run_service()
