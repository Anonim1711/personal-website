// Floating particle background + cursor glow, standalone (no framework).
// Mirrors the index page's setupParticles so every page shares one look.
// Include with <script src="./particles.js" defer></script>. Colors: cream
// #EAE7DF (234,231,223) + rust #C6432B (198,67,43) on #0B0B0C.
(function () {
  if (window.__particlesInit) return;           // ponytail: guard double-include
  window.__particlesInit = true;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion:reduce)').matches) return;

  function start() {
    // Attach to <body>, NOT inside the page markup: the DC runtime renders
    // into a React-owned #dc-root and wipes any child it doesn't manage on
    // re-render. A body-level sibling survives. The page's root wrapper is set
    // to transparent background so this fixed canvas (z-index 0) shows through.
    var canvas = document.createElement('canvas');
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none;';
    var glow = document.createElement('div');
    glow.setAttribute('aria-hidden', 'true');
    glow.style.cssText = 'position:fixed;top:0;left:0;width:620px;height:620px;margin:-310px 0 0 -310px;border-radius:50%;background:radial-gradient(circle,rgba(198,67,43,.16),transparent 62%);pointer-events:none;z-index:1;opacity:0;transition:opacity .5s ease;will-change:transform;';
    document.body.appendChild(canvas);
    document.body.appendChild(glow);

    var ctx = canvas.getContext('2d');
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    var pw, ph, parts;
    function resize() {
      pw = window.innerWidth; ph = window.innerHeight;
      canvas.width = pw * dpr; canvas.height = ph * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var count = Math.max(28, Math.min(88, Math.round(pw * ph / 20000)));
      parts = Array.from({ length: count }, function () {
        return {
          x: Math.random() * pw, y: Math.random() * ph,
          vx: (Math.random() - 0.5) * 0.28, vy: (Math.random() - 0.5) * 0.28,
          r: Math.random() * 1.4 + 0.9, cream: Math.random() < 0.28
        };
      });
    }
    resize();
    window.addEventListener('resize', resize);

    var mouse = { x: -999, y: -999, has: false };
    if (window.matchMedia && window.matchMedia('(pointer:fine)').matches) {
      window.addEventListener('pointermove', function (e) {
        glow.style.opacity = '1';
        glow.style.transform = 'translate(' + e.clientX + 'px,' + e.clientY + 'px)';
        mouse.x = e.clientX; mouse.y = e.clientY; mouse.has = true;
      }, { passive: true });
    }

    var LINK = 132, MOUSE = 190;
    function loop() {
      var ps = parts, W = pw, H = ph, m = mouse, i, j;
      ctx.clearRect(0, 0, W, H);
      for (i = 0; i < ps.length; i++) {
        var p = ps[i];
        p.x += p.vx; p.y += p.vy;
        if (p.x < -20) p.x = W + 20; else if (p.x > W + 20) p.x = -20;
        if (p.y < -20) p.y = H + 20; else if (p.y > H + 20) p.y = -20;
      }
      for (i = 0; i < ps.length; i++) {
        var a = ps[i];
        for (j = i + 1; j < ps.length; j++) {
          var b = ps[j];
          var dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
          if (d2 < LINK * LINK) {
            var al = (1 - Math.sqrt(d2) / LINK) * 0.34;
            ctx.strokeStyle = 'rgba(198,67,43,' + al.toFixed(3) + ')';
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
        if (m.has) {
          var mdx = a.x - m.x, mdy = a.y - m.y, md2 = mdx * mdx + mdy * mdy;
          if (md2 < MOUSE * MOUSE) {
            var mal = (1 - Math.sqrt(md2) / MOUSE) * 0.5;
            ctx.strokeStyle = 'rgba(234,231,223,' + mal.toFixed(3) + ')';
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(m.x, m.y); ctx.stroke();
          }
        }
      }
      for (i = 0; i < ps.length; i++) {
        var q = ps[i];
        ctx.beginPath(); ctx.arc(q.x, q.y, q.r, 0, Math.PI * 2);
        ctx.fillStyle = q.cream ? 'rgba(234,231,223,.5)' : 'rgba(198,67,43,.7)';
        ctx.fill();
      }
      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
