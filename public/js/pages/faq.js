// faq.html — live search filter across all questions + sidebar category nav.
(function () {
  const searchInput = document.getElementById('faqSearch');
  const items = document.querySelectorAll('.faq-item');
  const groups = document.querySelectorAll('.faq-cat-group');
  const noResults = document.getElementById('faqNoResults');
  const sidebarLinks = document.querySelectorAll('.faq-sidebar-link');

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      let visibleCount = 0;

      items.forEach((item) => {
        const match = !q || item.dataset.q.includes(q);
        item.classList.toggle('faq-hidden', !match);
        if (match) visibleCount++;
      });

      groups.forEach((group) => {
        const anyVisible = group.querySelectorAll('.faq-item:not(.faq-hidden)').length > 0;
        group.classList.toggle('faq-hidden', !anyVisible);
      });

      if (noResults) noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    });
  }

  sidebarLinks.forEach((link) => {
    link.addEventListener('click', (e) => {
      sidebarLinks.forEach((l) => l.classList.remove('active'));
      link.classList.add('active');
      if (link.dataset.cat !== 'all') return; // let the browser handle the #anchor scroll
      e.preventDefault();
      if (searchInput) { searchInput.value = ''; searchInput.dispatchEvent(new Event('input')); }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
})();
