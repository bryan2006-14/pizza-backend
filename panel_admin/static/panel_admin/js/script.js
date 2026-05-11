// ============================================================
// SIDEBAR — lógica unificada (clase "collapsed" en todo el stack)
// ============================================================

const sidebar      = document.querySelector('#sidebar');
const mainContent  = document.querySelector('#contenido_principal');
const hamBurger    = document.querySelector('.toggle-btn');

// Overlay para cerrar el sidebar en móvil al tocar fuera
const overlay = document.createElement('div');
overlay.id = 'sidebar-overlay';
overlay.style.cssText = [
  'position:fixed', 'inset:0', 'background:rgba(0,0,0,0.4)',
  'z-index:999', 'display:none', 'opacity:0',
  'transition:opacity 0.3s ease',
].join(';');
document.body.appendChild(overlay);

function isMobile() {
  return window.innerWidth < 768;
}

function openSidebar() {
  if (isMobile()) {
    sidebar.classList.add('show');
    overlay.style.display = 'block';
    requestAnimationFrame(() => { overlay.style.opacity = '1'; });
  } else {
    sidebar.classList.remove('collapsed');
  }
  hamBurger.setAttribute('aria-expanded', 'true');
}

function closeSidebar() {
  if (isMobile()) {
    sidebar.classList.remove('show');
    overlay.style.opacity = '0';
    setTimeout(() => { overlay.style.display = 'none'; }, 300);
  } else {
    sidebar.classList.add('collapsed');
  }
  hamBurger.setAttribute('aria-expanded', 'false');
}

hamBurger.addEventListener('click', () => {
  const isOpen = isMobile()
    ? sidebar.classList.contains('show')
    : !sidebar.classList.contains('collapsed');

  isOpen ? closeSidebar() : openSidebar();
});

overlay.addEventListener('click', closeSidebar);
mainContent.addEventListener('click', () => {
  if (isMobile() && sidebar.classList.contains('show')) closeSidebar();
});

// Cerrar submenús huérfanos al hacer resize
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (!isMobile()) {
      overlay.style.display = 'none';
      sidebar.classList.remove('show');
    }
  }, 150);
});

// ============================================================
// TOASTR — leer mensajes Django correctamente
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  const djangoMessages = document.getElementById('django-messages');
  if (!djangoMessages) return;

  djangoMessages.querySelectorAll('[data-level][data-text]').forEach(el => {
    const level = el.dataset.level;
    const text  = el.dataset.text;
    const map   = { success: 'success', error: 'error', warning: 'warning', info: 'info' };
    const fn    = map[level] || 'info';
    if (typeof toastr !== 'undefined') toastr[fn](text);
  });
});