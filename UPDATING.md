### To release a new version of the addon, follow these steps:

1. Update the version number in the plugin.video.tidb/addon.xml file.
2. Copy the plugin.video.tidb/addon.xml addon manifest to the addons.xml file.
3. Run `md5 -q addons.xml > addons.xml.md5` (for the root manifest)
4. Zip the plugin.video.tidb folder and rename it to `plugin.video.tidb-[version].zip`
5. Move the zip file to the /docs folder and update index.html with the new version

Kodi will detect a version difference in the addons.xml file and prompt you to update the addon. It pulls from the github pages URL to download the latest version of the addon.