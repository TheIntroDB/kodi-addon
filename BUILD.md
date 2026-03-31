# Maintainer notes (releases & GitHub Pages)

## Turn on github.io (one-time)

The site **`https://jzonethegit.github.io/Smart-Intro-Skip/`** is served from **`docs/`** via **GitHub Pages**.

1. GitHub repo → **Settings** → **Pages**
2. **Source**: *Deploy from a branch* → **Branch**: `main` → **Folder**: `/docs` → **Save**
3. Wait for the build; check **Actions** if it 404s at first.

**Layout:** `addons.xml` and checksums stay in **`docs/`** root (what Kodi’s repo uses). **Zips** are in **`docs/zips/`**. **`docs/zips/index.html`** is required so **`/zips/`** does not 404 on GitHub Pages (folders need an `index.html`). The site root **`docs/index.html`** is the minimal download page.

The repository addon uses **`.../zips/`** for `datadir` so Kodi pulls **`plugin.video.introskip-X.Y.Z.zip`** from there (filename must match id + version).

## Release checklist

1. Bump **`version`** in **`plugin.video.introskip/addon.xml`**
2. Copy the `<addon>...</addon>` block into **`docs/addons.xml`**
3. From project root:
   ```bash
   rm -f docs/zips/plugin.video.introskip-*.zip
   zip -r docs/zips/plugin.video.introskip-X.Y.Z.zip plugin.video.introskip
   md5 -q docs/addons.xml > docs/addons.xml.md5
   ```
4. If **`repository.smartintro.jz/addon.xml`** changed, rebuild the **named** repository installer:
   ```bash
   rm -f docs/zips/01-install-this-first-repository.smartintro.jz-*.zip
   zip -r docs/zips/01-install-this-first-repository.smartintro.jz-1.0.0.zip repository.smartintro.jz
   ```
5. Update **`docs/index.html`** and **`docs/zips/index.html`** if zip names or versions changed
6. Commit and push **`main`**

Repo must stay **public** for Pages and for Kodi to fetch files.
