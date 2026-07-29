// home.html — scroll-reveal animation + lazy video modal.
(function () {
  const revealEls = document.querySelectorAll('.reveal');
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          observer.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  revealEls.forEach((el) => observer.observe(el));

  const videoModal = document.getElementById('videoModal');
  if (videoModal) {
    const embedUrl = window.HOME_VIDEO_EMBED_URL || '';
    videoModal.addEventListener('show.bs.modal', () => {
      document.getElementById('videoModalIframe').src = embedUrl + (embedUrl.includes('?') ? '&' : '?') + 'autoplay=1';
    });
    videoModal.addEventListener('hidden.bs.modal', () => {
      document.getElementById('videoModalIframe').src = '';
    });
  }
})();
