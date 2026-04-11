# TheIntroDB – Kodi Addon

<p align="center">
  <img src="https://raw.githubusercontent.com/TheIntroDB/theintrodb-assets/main/logo-banner.png">
</p>

Kodi service add-on that gets intro segments from **[TheIntroDB](https://theintrodb.org)** and either shows a **Skip intro** control or **auto-skips** it.

**Requirements:** Kodi 19+. **TMDb metadata is recommended** for best accuracy. IMDb works as a fallback for supported items.

**Important:** Lookups happen when playback starts. If the current item does not expose a usable **TMDb** or **IMDb** ID, the add-on cannot match it with TheIntroDB.

**Troubleshooting (no skip button):** See the Metadata Requirements and Installation sections below.

---

## Installation

### Option A: Add repository (automatic updates)

1. In Kodi, go to **Settings → Add-ons → Install from zip file**.
2. Download the repository zip from:
   `https://theintrodb.github.io/kodi-addon/zips/01-install-this-first-repository.tidb.repo-1.0.7.zip`
3. Install the zip, then go to **Install from repository**.
4. Open **TheIntroDB Kodi Repository** and install **TheIntroDB Kodi Addon**.
5. Allow third-party repository updates under **Settings → System → Add-ons** if you want automatic updates.

### Option B: Add-on zip only

1. Download the latest add-on zip from:
   `https://theintrodb.github.io/kodi-addon/zips/plugin.video.tidb-1.2.1.zip`
2. In Kodi, choose **Settings → Add-ons → Install from zip file**.
3. Select the zip to install the add-on directly.

### Option C: Copy into the Kodi add-ons folder

1. Unzip or copy the add-on folder named `plugin.video.tidb` into Kodi’s add-ons directory for your platform.
2. Restart Kodi or reload add-ons.

---

### Metadata Requirements

**TMDB is recommended.** The add-on prefers TMDB IDs for matching. If TMDB is unavailable, it can fall back to IMDb `tt...` IDs.

For TV episodes, the playing item also needs valid **season** and **episode** numbers. If your source add-on or library does not expose provider IDs, TheIntroDB cannot match the item.

## Features

- **Skip intro** button during the intro window
- **Auto-skip** mode that seeks past the intro without showing the button
- **Optional API key** support for TheIntroDB
- **Debug logging and on-screen notifications** for troubleshooting

## How It Works

On each new playback, the add-on reads what Kodi exposes for the current item through JSON-RPC `Player.GetItem` and `VideoInfoTag`: **TMDb ID** when available, otherwise **IMDb** `tt...` ID, plus **season** and **episode** for TV content.

It then calls TheIntroDB, retrieves intro **start** and **end** times, waits until the intro window begins, and either shows the skip overlay or seeks automatically depending on your settings.

## Configuration

TheIntroDB Kodi Addon includes a few settings to adjust behavior:

- **Auto-skip**: Skip without showing the button
- **Extra seconds after intro end**: Adds a small offset to the skip target
- **Enable lookups**: Turns TheIntroDB requests on or off
- **API key**: Lets you use your TheIntroDB API key if required
- **Debug options**: Enables verbose logging and on-screen notifications

---

## Credits

- **TheIntroDB** — database and API: [theintrodb.org](https://theintrodb.org) · [github.com/TheIntroDB](https://github.com/TheIntroDB)
- **JZOnTheGit** — original addon creator: [github.com/JZOnTheGit](https://github.com/JZOnTheGit)

## License

See [LICENSE](LICENSE) for details.
