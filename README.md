# Smart Intro Skip

<p align="center">
  <img src="plugin.video.introskip/resources/icon.png" alt="Smart Intro Skip" width="160" height="160">
</p>

Kodi service add-on that looks up intro start/end from **[TheIntroDB](https://theintrodb.org)** and either shows a **Skip intro** control or **auto-skips** (optional).

## Credits

- **TheIntroDB** — database and API: [theintrodb.org](https://theintrodb.org) · [github.com/TheIntroDB](https://github.com/TheIntroDB)  
- **Pasithea0** — API creator / maintainer: [github.com/Pasithea0](https://github.com/Pasithea0)  

This add-on is a separate Kodi client; it is not run or hosted by TheIntroDB.

## Installation

**1. Repository (updates from Kodi)**  

- Zips: [jzonthegit.github.io/Smart-Intro-Skip/zips](https://jzonthegit.github.io/Smart-Intro-Skip/zips/)  
- File source URL: `https://jzonthegit.github.io/Smart-Intro-Skip/zips/`  
- Install **`01-install-this-first-repository.smartintro.jz-….zip`** from **Settings → Add-ons → Install from zip file**, then **Install from repository** → **Smart Intro Skip repo** → **Smart Intro Skip**.

**2. Add-on zip only**  

- Download **`plugin.video.introskip-….zip`** from the same **zips** folder and install from zip.

**3. Copy into the Kodi add-ons folder**  

- Unzip or copy the add-on folder (named `plugin.video.introskip`) into Kodi’s `addons` directory for your platform, then restart Kodi or reload add-ons. Same layout as a zip install.

Allow third-party repo updates under **Settings → System → Add-ons** if you want automatic updates from the repo.

## Features

- **Skip intro** button for the intro window (default).  
- **Auto-skip** — optional; seeks past the intro without showing the button.

## How it works

On each new play, the service reads **what Kodi’s player exposes** for the current item (via JSON-RPC `Player.GetItem` and `VideoInfoTag`): **TMDB id** (preferred) or **IMDb** `tt…` id, plus **season** and **episode** for TV. It calls TheIntroDB once, gets intro **start/end** times, waits until roughly **start**, then shows the button or seeks.  

If the playing item has **no usable ids** (many add-ons only set a title and not `uniqueid`), the add-on cannot match — that has to come from the source add-on or library metadata.

## Settings

| | |
|--|--|
| **General** | Auto-skip; extra seconds after intro end |
| **TheIntroDB** | Enable lookups; API key if the site requires it |
| **Debug** | Extra logging / on-screen notifications |

## Requirements

- Kodi **19+** (Python 3)  
- Items with **TMDB or IMDb** id where relevant, and **season/episode** for TV episodes  

## License

GPL-2.0-or-later
