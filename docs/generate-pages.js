#!/usr/bin/env node

/**
 * Generate static version folders for GitHub Pages
 * This script creates folder structures that mimic a traditional file server
 * but link to GitHub release downloads instead of hosting files directly.
 */

const fs = require('fs');
const path = require('path');

const GITHUB_API_URL = 'https://api.github.com/repos/TheIntroDB/kodi-addon/releases';

// Base directory for docs
const DOCS_DIR = path.join(__dirname, '..', 'docs');

async function fetchReleases() {
  try {
    const response = await fetch(GITHUB_API_URL);
    if (!response.ok) {
      throw new Error(`GitHub API error: ${response.status} ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch releases:', error.message);
    return [];
  }
}

function generateVersionIndex(release) {
  const version = release.tag_name;
  const assets = release.assets;
  
  // Filter to only show plugin files, not repository files
  const pluginAssets = assets.filter(asset => 
    asset.name === 'plugin.video.tidb.zip' || 
    asset.name === 'addons.xml' || 
    asset.name === 'addons.xml.md5'
  );
  
  let html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Index of /${version}/</title>
</head>
<body>
<h1>Index of /${version}/</h1><hr>
<pre>
<a href="../">../</a>`;

  pluginAssets.forEach(asset => {
    html += `\n<a href="${asset.browser_download_url}">${asset.name}</a>`;
  });

  html += `
</pre><hr>
</body>
</html>`;

  return html;
}

async function generateStaticPages() {
  console.log('Fetching releases from GitHub...');
  const releases = await fetchReleases();
  
  if (releases.length === 0) {
    console.log('No releases found or error occurred. Skipping generation.');
    return;
  }
  
  console.log(`Found ${releases.length} releases`);
  
  // Create version folders and index files
  for (const release of releases) {
    const version = release.tag_name;
    const versionDir = path.join(DOCS_DIR, version);
    
    // Create version directory
    if (!fs.existsSync(versionDir)) {
      fs.mkdirSync(versionDir, { recursive: true });
      console.log(`Created directory: ${version}/`);
    }
    
    // Generate index.html for this version
    const indexContent = generateVersionIndex(release);
    const indexPath = path.join(versionDir, 'index.html');
    
    fs.writeFileSync(indexPath, indexContent);
    console.log(`Generated: ${version}/index.html`);
  }
  
  console.log('Static page generation complete!');
}

// Run the generation
if (require.main === module) {
  generateStaticPages().catch(error => {
    console.error('Generation failed:', error);
    process.exit(1);
  });
}

module.exports = { generateStaticPages, fetchReleases };