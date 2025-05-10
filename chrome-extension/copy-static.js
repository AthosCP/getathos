const fs = require('fs');
const path = require('path');

const filesToCopy = [
  'manifest.json',
  'icon16.png',
  'icon32.png',
  'icon48.png',
  'icon128.png'
];

const distDir = path.join(__dirname, 'dist');

if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir);
}

for (const file of filesToCopy) {
  const src = path.join(__dirname, file);
  const dest = path.join(distDir, file);
  fs.copyFileSync(src, dest);
  console.log(`Copiado: ${file} -> dist/${file}`);
}

// Copiar y modificar popup.html
const popupSrc = path.join(__dirname, 'dist/src/popup.html');
const popupDest = path.join(distDir, 'popup.html');
if (fs.existsSync(popupSrc)) {
  let popupHtml = fs.readFileSync(popupSrc, 'utf8');
  popupHtml = popupHtml.replace('src="./popup.ts"', 'src="popup.js"');
  fs.writeFileSync(popupDest, popupHtml);
  console.log('Copiado y modificado: popup.html -> dist/popup.html');
}

// Copiar blocked.html sin cambios
const blockedSrc = path.join(__dirname, 'dist/src/blocked.html');
const blockedDest = path.join(distDir, 'blocked.html');
if (fs.existsSync(blockedSrc)) {
  fs.copyFileSync(blockedSrc, blockedDest);
  console.log('Copiado: blocked.html -> dist/blocked.html');
} 