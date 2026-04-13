const https = require('https');

const GITHUB_API_URL = 'https://api.github.com/repos/TheIntroDB/kodi-addon/releases';

function fetchReleases() {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'GitHub-Actions-Generator',
        'Accept': 'application/vnd.github.v3+json'
      }
    };
    
    https.get(GITHUB_API_URL, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error('Failed to parse JSON'));
        }
      });
    }).on('error', reject);
  });
}

async function buildIndex() {
  try {
    console.log('Fetching releases from GitHub...');
    const releases = await fetchReleases();
    
    if (releases.length === 0) {
      console.log('No releases found');
      return;
    }
    
    // Sort releases by version (newest first)
    releases.sort((a, b) => b.tag_name.localeCompare(a.tag_name));
    
    // Generate plugin links HTML
    let pluginLinksHtml = '';
    
    releases.forEach(release => {
      const pluginAsset = release.assets.find(asset => asset.name === 'plugin.video.tidb.zip');
      if (pluginAsset) {
        pluginLinksHtml += `<a href="${pluginAsset.browser_download_url}">plugin.video.tidb-${release.tag_name}.zip</a>\n`;
      }
    });
    
    // Read the current index.html
    const fs = require('fs');
    let indexContent = fs.readFileSync('index.html', 'utf8');
    
    // Replace the placeholder with actual plugin links
    indexContent = indexContent.replace(
      '<div id="plugin-links">\n  <!-- Plugin links will be inserted here by GitHub Actions -->\n</div>',
      `<pre>\n${pluginLinksHtml}</pre>`
    );
    
    // Write the updated index.html
    fs.writeFileSync('index.html', indexContent);
    console.log('Updated index.html with plugin links');
    
    // Generate version folders
    for (const release of releases) {
      const version = release.tag_name;
      const versionDir = version;
      
      // Create version directory
      if (!fs.existsSync(versionDir)) {
        fs.mkdirSync(versionDir, { recursive: true });
        console.log(`Created directory: ${version}/`);
      }
      
      // Generate version index.html
      const pluginAssets = release.assets.filter(asset => 
        asset.name === 'plugin.video.tidb.zip' || 
        asset.name === 'addons.xml' || 
        asset.name === 'addons.xml.md5'
      );
      
      let versionHtml = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Index of /${version}/</title></head><body><h1>Index of /${version}/</h1><pre><a href="../">../</a>`;
      
      pluginAssets.forEach(asset => {
        versionHtml += `\n<a href="${asset.browser_download_url}">${asset.name}</a>`;
      });
      
      versionHtml += `</pre></body></html>`;
      
      fs.writeFileSync(`${versionDir}/index.html`, versionHtml);
      console.log(`Generated: ${version}/index.html`);
    }
    
    console.log('Static page generation complete!');
    
  } catch (error) {
    console.error('Generation failed:', error);
    process.exit(1);
  }
}

buildIndex();
