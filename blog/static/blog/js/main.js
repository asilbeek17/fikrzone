/* ════════════════════════════════════════════════════════════════════════════
   EDITORIAL v2 — main.js
   ════════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── Theme ────────────────────────────────────────────────────────────── */
  const html      = document.documentElement;
  const themeBtn  = document.getElementById('themeToggle');
  const themeIcon = document.getElementById('themeIcon');

  function applyTheme(t) {
    html.setAttribute('data-theme', t);
    localStorage.setItem('ed-theme', t);
    if (themeIcon) themeIcon.className = t === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
  }
  applyTheme(localStorage.getItem('ed-theme') || 'light');
  if (themeBtn) themeBtn.addEventListener('click', () => {
    applyTheme(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  /* ── Sidebar ──────────────────────────────────────────────────────────── */
  const sidebar    = document.getElementById('edSidebar');
  const layout     = document.getElementById('edLayout');
  const footer     = document.getElementById('edFooter');
  const toggleBtn  = document.getElementById('sidebarToggle');
  const isMobile   = () => window.innerWidth <= 900;

  function getSaved()  { return localStorage.getItem('ed-sidebar') || 'open'; }
  function setSaved(s) { localStorage.setItem('ed-sidebar', s); }

  function openSidebar() {
    if (isMobile()) {
      sidebar.classList.add('mobile-open');
      sidebar.classList.remove('collapsed');
    } else {
      sidebar.classList.remove('collapsed');
      layout.classList.remove('sidebar-collapsed');
      if (footer) footer.style.marginLeft = 'var(--sidebar-w)';
    }
    setSaved('open');
  }

  function closeSidebar() {
    if (isMobile()) {
      sidebar.classList.remove('mobile-open');
    } else {
      sidebar.classList.add('collapsed');
      layout.classList.add('sidebar-collapsed');
      if (footer) footer.style.marginLeft = '0';
    }
    setSaved('closed');
  }

  function toggle() {
    if (isMobile()) {
      sidebar.classList.contains('mobile-open') ? closeSidebar() : openSidebar();
    } else {
      sidebar.classList.contains('collapsed') ? openSidebar() : closeSidebar();
    }
  }

  // Init state
  if (sidebar && !isMobile()) {
    if (getSaved() === 'closed') {
      sidebar.classList.add('collapsed');
      layout.classList.add('sidebar-collapsed');
      if (footer) footer.style.marginLeft = '0';
    }
  }

  if (toggleBtn) toggleBtn.addEventListener('click', toggle);

  // Close on outside tap (mobile)
  document.addEventListener('click', e => {
    if (!isMobile() || !sidebar) return;
    if (sidebar.classList.contains('mobile-open') && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) closeSidebar();
  });

  window.addEventListener('resize', () => {
    if (!sidebar || isMobile()) return;
    sidebar.classList.remove('mobile-open');
    if (getSaved() === 'closed') {
      sidebar.classList.add('collapsed');
      layout.classList.add('sidebar-collapsed');
      if (footer) footer.style.marginLeft = '0';
    } else {
      sidebar.classList.remove('collapsed');
      layout.classList.remove('sidebar-collapsed');
      if (footer) footer.style.marginLeft = 'var(--sidebar-w)';
    }
  });

  /* ── Count published posts for sidebar stat ───────────────────────────── */
  const pubCountEl = document.getElementById('pubCount');
  if (pubCountEl) {
    const items = document.querySelectorAll('.ed-post-list__item');
    const drafts = document.querySelectorAll('.ed-post-list__draft').length;
    pubCountEl.textContent = items.length - drafts;
  }

  /* ── Navbar scroll shadow ─────────────────────────────────────────────── */
  const navbar = document.getElementById('edNavbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.style.boxShadow = window.scrollY > 8 ? '0 2px 16px rgba(0,0,0,0.08)' : 'none';
    }, { passive: true });
  }

  /* ── Scroll active sidebar item into view ─────────────────────────────── */
  const active = document.querySelector('.ed-post-list__item.active');
  if (active && sidebar) setTimeout(() => active.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 150);

  /* ── Auto-dismiss messages ────────────────────────────────────────────── */
  document.querySelectorAll('.ed-message').forEach(msg => {
    setTimeout(() => {
      msg.style.transition = 'opacity 0.35s, transform 0.35s';
      msg.style.opacity = '0';
      msg.style.transform = 'translateY(-8px)';
      setTimeout(() => msg.remove(), 370);
    }, 4500);
  });

})();
