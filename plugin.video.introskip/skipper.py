# seek to intro end + offset from settings
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon()


def execute_skip(player, intro_start, intro_end, filename=None):
    if not player.isPlaying():
        return False

    offset = int(ADDON.getSetting('skip_offset') or 2)
    target = intro_end + offset

    total_time = player.getTotalTime()
    if target >= total_time:
        target = total_time - 10

    xbmc.log('[IntroSkip] Skipping intro: {:.1f}s -> {:.1f}s (target {:.1f}s)'.format(
        intro_start, intro_end, target), xbmc.LOGINFO)

    player.seekTime(target)
    return True
