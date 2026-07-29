// site.js — shared behaviour for every page (navbar shadow, back-to-top, toasts).
(function () {
  const navbar = document.getElementById('navbar');
  const backTop = document.getElementById('back-top');

  if (navbar || backTop) {
    window.addEventListener('scroll', () => {
      if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 20);
      if (backTop) backTop.classList.toggle('show', window.scrollY > 300);
    });
  }

  setTimeout(() => {
    document.querySelectorAll('#toast-stack .alert').forEach((el) => { el.style.display = 'none'; });
  }, 6000);
})();
