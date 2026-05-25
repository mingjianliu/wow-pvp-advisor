const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8080;
const PUBLIC_DIR = path.resolve(__dirname, '../../frontend');

const MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.jsx': 'text/javascript',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.json': 'application/json',
};

const server = http.createServer((req, res) => {
  const safeUrl = req.url.split('?')[0];
  let fileToLoad = safeUrl === '/' ? '/index.html' : safeUrl;
  
  // Intercept Chinese translation URL to serve the same index.html
  // but keeping the pathname _zh.html so React switches to zh_CN locale
  if (fileToLoad === '/index_zh.html') {
    fileToLoad = '/index.html';
  }

  const filePath = path.join(PUBLIC_DIR, fileToLoad);

  // Prevent directory traversal
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.statusCode = 403;
    res.end('Forbidden');
    return;
  }

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.statusCode = 404;
      res.end('Not Found');
      return;
    }
    const ext = path.extname(filePath);
    res.setHeader('Content-Type', MIME_TYPES[ext] || 'text/plain');
    res.end(content);
  });
});

server.listen(PORT, () => {
  console.log(`Visual Test Server is running at http://localhost:${PORT}/`);
});
