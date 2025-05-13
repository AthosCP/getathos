const fs = require('fs');
const path = require('path');

const distHtml = path.join(__dirname, 'dist/popup.html');
if (fs.existsSync(distHtml)) {
  let html = fs.readFileSync(distHtml, 'utf8');
  html = html.replace('src="./popup.ts"', 'src="popup.js"');
  fs.writeFileSync(distHtml, html, 'utf8');
  console.log('Referencia a popup.js corregida en dist/popup.html');
} else {
  console.error('No se encontró dist/popup.html');
} 