/* ============================================
   HUNTERSTAR FILE TRANSFER — SCRIPT
   Sections:
   1. Status bar clock
   2. Background particle canvas
   3. Hero network visualization
   4. Mouse parallax (floating cards + blobs)
   5. Nav scroll state + mobile toggle
   6. Smooth scroll
   7. Reveal on scroll
   8. Counter animations
   9. Feature card mouse glow
   ============================================ */

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ===== 1. STATUS BAR CLOCK ===== */
function updateClock() {
  const now = new Date();
  const h = String(now.getUTCHours()).padStart(2, '0');
  const m = String(now.getUTCMinutes()).padStart(2, '0');
  const s = String(now.getUTCSeconds()).padStart(2, '0');
  const el = document.getElementById('status-time');
  if (el) el.textContent = `${h}:${m}:${s} UTC`;
}
updateClock();
setInterval(updateClock, 1000);

/* ===== 2. BACKGROUND PARTICLE CANVAS ===== */
(function particleBackground() {
  const canvas = document.getElementById('particle-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let w, h, particles = [];
  const PARTICLE_COUNT = window.innerWidth < 768 ? 25 : 60;

  function resize() {
    w = canvas.width = window.innerWidth * window.devicePixelRatio;
    h = canvas.height = window.innerHeight * window.devicePixelRatio;
    canvas.style.width = window.innerWidth + 'px';
    canvas.style.height = window.innerHeight + 'px';
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  }
  resize();
  window.addEventListener('resize', resize);

  function spawn() {
    return {
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      vx: (Math.random() - 0.5) * 0.15,
      vy: (Math.random() - 0.5) * 0.15,
      size: Math.random() * 1.4 + 0.3,
      opacity: Math.random() * 0.4 + 0.1,
      twinkle: Math.random() * Math.PI * 2
    };
  }

  for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(spawn());

  function draw() {
    ctx.clearRect(0, 0, w, h);
    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.twinkle += 0.02;
      if (p.x < 0) p.x = window.innerWidth;
      if (p.x > window.innerWidth) p.x = 0;
      if (p.y < 0) p.y = window.innerHeight;
      if (p.y > window.innerHeight) p.y = 0;

      const alpha = p.opacity * (0.5 + Math.sin(p.twinkle) * 0.5);
      ctx.fillStyle = `rgba(255, 26, 26, ${alpha})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    });
    if (!prefersReducedMotion) requestAnimationFrame(draw);
  }
  draw();
})();

/* ===== 3. HERO NETWORK VISUALIZATION ===== */
(function networkViz() {
  const canvas = document.getElementById('network-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let w, h, nodes = [], particles = [];
  let mouse = { x: 0, y: 0 };
  const NODE_COUNT = 14;

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    w = canvas.width = rect.width * window.devicePixelRatio;
    h = canvas.height = rect.height * window.devicePixelRatio;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    canvas.dispW = rect.width;
    canvas.dispH = rect.height;
  }
  resize();
  window.addEventListener('resize', resize);

  // Initialize nodes
  for (let i = 0; i < NODE_COUNT; i++) {
    const x = Math.random() * canvas.dispW;
    const y = Math.random() * canvas.dispH;
    nodes.push({
      x, y, baseX: x, baseY: y,
      isFolder: Math.random() > 0.6,
      pulse: Math.random() * Math.PI * 2,
      connections: []
    });
  }

  // Build connections (proximity-based)
  nodes.forEach((node, i) => {
    nodes.forEach((other, j) => {
      if (i === j) return;
      const d = Math.hypot(node.baseX - other.baseX, node.baseY - other.baseY);
      if (d < 200 && Math.random() > 0.55) {
        node.connections.push(j);
      }
    });
  });

  canvas.addEventListener('mousemove', e => {
    const rect = canvas.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });

  canvas.addEventListener('mouseleave', () => {
    mouse.x = canvas.dispW / 2;
    mouse.y = canvas.dispH / 2;
  });

  function spawnParticle() {
    if (particles.length > 12) return;
    const fromIdx = Math.floor(Math.random() * nodes.length);
    const node = nodes[fromIdx];
    if (!node.connections.length) return;
    const toIdx = node.connections[Math.floor(Math.random() * node.connections.length)];
    particles.push({
      from: fromIdx,
      to: toIdx,
      progress: 0,
      speed: 0.008 + Math.random() * 0.012
    });
  }
  setInterval(spawnParticle, 280);

  function drawNode(node) {
    const pulseSize = Math.sin(node.pulse) * 0.3 + 1;
    // Outer glow
    const g = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, 18);
    g.addColorStop(0, 'rgba(176, 0, 32, 0.35)');
    g.addColorStop(1, 'rgba(176, 0, 32, 0)');
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(node.x, node.y, 18 * pulseSize, 0, Math.PI * 2);
    ctx.fill();

    // Icon
    if (node.isFolder) {
      ctx.strokeStyle = '#B00020';
      ctx.lineWidth = 1.2;
      ctx.fillStyle = 'rgba(15, 15, 15, 0.9)';
      const s = 6;
      ctx.beginPath();
      ctx.rect(node.x - s, node.y - s * 0.7, s * 2, s * 1.4);
      ctx.fill();
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(node.x - s, node.y - s * 0.7);
      ctx.lineTo(node.x - s * 0.3, node.y - s * 0.7;
      ctx.lineTo(node.x, node.y - s * 1.2);
      ctx.lineTo(node.x + s, node.y - s * 1.2);
      ctx.stroke();
    } else {
      ctx.fillStyle = 'rgba(15, 15, 15, 0.9)';
      ctx.strokeStyle = '#B00020';
      ctx.lineWidth = 1.2;
      const s = 5;
      ctx.beginPath();
      ctx.rect(node.x - s, node.y - s, s * 2, s * 2);
      ctx.fill();
      ctx.stroke();
      // Corner fold
      ctx.beginPath();
      ctx.moveTo(node.x + s - 2, node.y - s);
      ctx.lineTo(node.x + s, node.y - s + 2);
      ctx.stroke();
    }

    // Center dot
    ctx.fillStyle = '#ff1a1a';
    ctx.beginPath();
    ctx.arc(node.x, node.y, 1.2, 0, Math.PI * 2);
    ctx.fill();
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.dispW, canvas.dispH);

    // Parallax offset
    const px = (mouse.x - canvas.dispW / 2) * 0.015;
    const py = (mouse.y - canvas.dispH / 2) * 0.015;

    nodes.forEach(node => {
      node.x = node.baseX + px;
      node.y = node.baseY + py;
      node.pulse += 0.025;
    });

    // Connections
    nodes.forEach((node, i) => {
      node.connections.forEach(j => {
        const other = nodes[j];
        ctx.strokeStyle = 'rgba(176, 0, 32, 0.12)';
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(node.x, node.y);
        ctx.lineTo(other.x, other.y);
        ctx.stroke();
      });
    });

    // Particles
    particles = particles.filter(p => {
      p.progress += p.speed;
      if (p.progress >= 1) return false;
      const from = nodes[p.from];
      const to = nodes[p.to];
      const x = from.x + (to.x - from.x) * p.progress;
      const y = from.y + (to.y - from.y) * p.progress;

      const grad = ctx.createRadialGradient(x, y, 0, x, y, 8);
      grad.addColorStop(0, 'rgba(255, 26, 26, 0.8)');
      grad.addColorStop(1, 'rgba(255, 26, 26, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#ff1a1a';
      ctx.beginPath();
      ctx.arc(x, y, 1.5, 0, Math.PI * 2);
      ctx.fill();
      return true;
    });

    // Nodes
    nodes.forEach(drawNode);

    if (!prefersReducedMotion) requestAnimationFrame(draw);
  }
  draw();
})();

/* ===== 4. MOUSE PARALLAX (FLOATING CARDS + BLOBS) ===== */
(function mouseParallax() {
  if (prefersReducedMotion) return;
  const cards = document.querySelectorAll('.float-card');
  const blobs = document.querySelectorAll('.bg-blob');
  let mx = 0, my = 0, tx = 0, ty = 0;

  document.addEventListener('mousemove', e => {
    mx = (e.clientX / window.innerWidth - 0.5) * 2;
    my = (e.clientY / window.innerHeight - 0.5) * 2;
  });

  function loop() {
    tx += (mx - tx) * 0.05;
    ty += (my - ty) * 0.05;

    cards.forEach(card => {
      const depth = parseFloat(card.dataset.depth) || 0.3;
      const baseTransform = card.style.transform || '';
      card.style.transform = `translate(${tx * depth * 20}px, ${ty * depth * 20}px)`;
    });

    blobs.forEach((blob, i) => {
      const depth = (i + 1) * 15;
      blob.style.transform = `translate(${tx * depth}px, ${ty * depth}px)`;
    });

    requestAnimationFrame(loop);
  }
  loop();
})();

/* ===== 5. NAV SCROLL + MOBILE TOGGLE ===== */
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  if (window.scrollY > 40) nav.classList.add('scrolled');
  else nav.classList.remove('scrolled');
});

const toggle = document.getElementById('nav-toggle');
const navLinks = document.getElementById('nav-links');
if (toggle) {
  toggle.addEventListener('click', () => {
    toggle.classList.toggle('active');
    navLinks.classList.toggle('open');
  });
}

navLinks.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => {
    toggle.classList.remove('active');
    navLinks.classList.remove('open');
  });
});

/* ===== 6. SMOOTH SCROLL ===== */
document.querySelectorAll('a[href^="#"]').forEach(link => {
  link.addEventListener('click', e => {
    const href = link.getAttribute('href');
    if (href === '#' || href.length < 2) return;
    const target = document.querySelector(href);
    if (target) {
      e.preventDefault();
      const offset = 80;
      const top = target.getBoundingClientRect().top + window.pageYOffset - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    }
  });
});

/* ===== 7. REVEAL ON SCROLL ===== */
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => entry.target.classList.add('revealed'), i * 60);
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('[data-reveal]').forEach(el => revealObserver.observe(el));

/* ===== 8. COUNTER ANIMATIONS ===== */
const counterObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const el = entry.target;
    const target = parseFloat(el.dataset.counter);
    const isFloat = target % 1 !== 0;
    let current = 0;
    const duration = 1400;
    const start = performance.now();

    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      current = target * eased;
      el.textContent = isFloat ? current.toFixed(1) : Math.floor(current).toLocaleString();
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
    counterObserver.unobserve(el);
  });
}, { threshold: 0.5 });

document.querySelectorAll('[data-counter]').forEach(el => counterObserver.observe(el));

/* ===== 9. FEATURE CARD MOUSE GLOW ===== */
document.querySelectorAll('.feature-card, .adv-card').forEach(card => {
  card.addEventListener('mousemove', e => {
    const rect = card.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    card.style.setProperty('--mx', x + '%');
    card.style.setProperty('--my', y + '%');
  });
});