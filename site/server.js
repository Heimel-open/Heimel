const http = require('http');
const fs = require('fs');
const path = require('path');

const port = process.env.PORT || 3000;
const root = __dirname;
const mime = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const visualsCss = `<style>
.visuals{border-bottom:1px solid var(--line)}
.visual-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--line)}
.visual-card{position:relative;min-height:360px;overflow:hidden;background:#171c1b}
.visual-card img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.visual-card:after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,26,25,.03) 38%,rgba(20,26,25,.82) 100%)}
.visual-copy{position:absolute;left:30px;right:30px;bottom:27px;z-index:1;color:#fff}
.visual-copy span{display:block;margin-bottom:6px;color:#d7d8d2;font-size:11px;letter-spacing:.13em;text-transform:uppercase}
.visual-copy strong{font-family:Georgia,serif;font-size:27px;font-weight:400;line-height:1.15}
.visual-card-tall{min-height:520px}
@media(max-width:980px){.visual-card{min-height:300px}.visual-card-tall{min-height:420px}}
@media(max-width:680px){.visual-grid{grid-template-columns:1fr}.visual-card,.visual-card-tall{min-height:330px}}
</style>`;

const visualsHtml = `<section class="visuals" aria-label="Heimel in consequential environments"><div class="visual-grid">
<article class="visual-card"><img src="assets/executive.webp" alt="Executives reviewing a consequential decision"><div class="visual-copy"><span>Executive authority</span><strong>Decisions with real consequence.</strong></div></article>
<article class="visual-card"><img src="assets/underwriting.svg" alt="Underwriting review and risk assessment"><div class="visual-copy"><span>Underwriting</span><strong>Authority before risk is bound.</strong></div></article>
<article class="visual-card"><img src="assets/factory.webp" alt="Industrial production line with robotic equipment"><div class="visual-copy"><span>Industrial systems</span><strong>Autonomy without a direct effect path.</strong></div></article>
<article class="visual-card"><img src="assets/claims.webp" alt="Claims review and evidence assessment"><div class="visual-copy"><span>Claims and evidence</span><strong>Every action attributable and replayable.</strong></div></article>
<article class="visual-card visual-card-tall"><img src="assets/shadow-mode.webp" alt="Heimel shadow mode"><div class="visual-copy"><span>Shadow mode</span><strong>Change when you know, not when you guess.</strong></div></article>
<article class="visual-card visual-card-tall"><img src="assets/intent-realized-office.webp" alt="Heimel office"><div class="visual-copy"><span>Heimel</span><strong>Our intent realized.</strong></div></article>
</div></section>`;

http.createServer((req, res) => {
  const raw = decodeURIComponent(req.url.split('?')[0]);
  const requested = raw === '/' ? '/index.html' : raw;
  const safe = path.normalize(requested).replace(/^([.][.][\/\\])+/, '');
  const filePath = path.join(root, safe);

  if (!filePath.startsWith(root)) {
    res.writeHead(403);
    return res.end('Forbidden');
  }

  fs.stat(filePath, (err, stat) => {
    if (err || !stat.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      return res.end('Not found');
    }

    if (filePath.endsWith('index.html')) {
      return fs.readFile(filePath, 'utf8', (readErr, source) => {
        if (readErr) {
          res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
          return res.end('Internal server error');
        }
        let html = source.replace('</head>', `${visualsCss}</head>`);
        html = html.replace('<section class="block" id="how">', `${visualsHtml}<section class="block" id="how">`);
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-cache' });
        return res.end(html);
      });
    }

    res.writeHead(200, {
      'Content-Type': mime[path.extname(filePath).toLowerCase()] || 'application/octet-stream',
      'Cache-Control': 'public, max-age=3600'
    });
    fs.createReadStream(filePath).pipe(res);
  });
}).listen(port, '0.0.0.0', () => {
  console.log(`HEIMEL site listening on ${port}`);
});
