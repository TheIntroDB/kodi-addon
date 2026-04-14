# TheIntroDB – Kodi Addon

<p align="center">
  <img src="https://raw.githubusercontent.com/TheIntroDB/theintrodb-assets/main/logo-banner.png">
</p>

Kodi service add-on that gets intro, recap, credits, and preview segments from **[TheIntroDB](https://theintrodb.org)** for movies and TV shows and shows a skip button or auto skips for you!

**Requirements:** Kodi 19+. **TMDb metadata is recommended** for best accuracy. IMDb works as a fallback for supported items.

**Important:** Lookups happen when playback starts. If the current item does not expose a usable **TMDb** or **IMDb** ID, the add-on cannot match it with TheIntroDB.

**Troubleshooting (no skip button):** See the Metadata Requirements and Installation sections below.

---

## Installation

### Option A: Add repository (automatic updates)

1. In Kodi, go to **Settings → Add-ons → Install from zip file**.
2. Download [repository.tidb.repo.zip](https://theintrodb.github.io/kodi-addon/repository.tidb.repo.zip) or add `https://theintrodb.github.io/kodi-addon/` as a source in the Kodi File Manager.
3. Install the zip, then go to **Install from repository**.
4. Open **TheIntroDB Kodi Addon Repo** and install **TheIntroDB Kodi Addon**.
5. Allow third-party repository updates under **Settings → System → Add-ons** if you want automatic updates.

### Option B: Add-on zip only

1. Download the latest add-on zip from [GitHub Releases](https://github.com/TheIntroDB/kodi-addon/releases/latest):
   - Look for `plugin.video.tidb.zip` in the latest release
   - Click to download the plugin zip file
2. In Kodi, choose **Settings → Add-ons → Install from zip file**.
3. Select the zip to install the add-on directly.

### Option C: Copy into the Kodi add-ons folder

1. Unzip or copy the add-on folder named `plugin.video.tidb` into Kodi’s add-ons directory for your platform.
2. Restart Kodi or reload add-ons.

---

### Metadata Requirements

**TMDB is recommended.** The add-on prefers TMDB IDs for matching. If TMDB is unavailable, it can fall back to IMDb `tt...` IDs.

For TV episodes, the playing item also needs valid **season** and **episode** numbers. If your source add-on or library does not expose provider IDs, TheIntroDB cannot match the item.

## How It Works

On each new playback, the add-on reads what Kodi exposes for the current item through JSON-RPC `Player.GetItem` and `VideoInfoTag`: **TMDb ID** when available, otherwise **IMDb** `tt...` ID, plus **season** and **episode** for TV content.

It then calls TheIntroDB, retrieves segment **start** and **end** times, waits until the segment window begins, and either shows the skip overlay or seeks automatically depending on your settings.

## Configuration

TheIntroDB Kodi Addon includes a few settings to adjust behavior:

- **Auto-skip**: Skip without showing the button
- **Extra seconds after segment end**: Adds a small offset to the skip target
- **Enable lookups**: Turns TheIntroDB requests on or off
- **API key**: Lets you use your TheIntroDB API key if required
- **Debug options**: Enables verbose logging and on-screen notifications

---

## Credits

- **TheIntroDB** — database and API: [theintrodb.org](https://theintrodb.org) · [github.com/TheIntroDB](https://github.com/TheIntroDB)
- **JZOnTheGit** — original addon creator: [github.com/JZOnTheGit](https://github.com/JZOnTheGit)

## License

See [LICENSE](LICENSE) for details.
