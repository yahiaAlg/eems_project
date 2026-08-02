// formateur_detail.html — hero entrance animation + lightbox preview for
// image-type certificate attachments (PDF certificates just open/download
// normally via their own <a target="_blank"> and are not included here).
(function () {
  if (window.gsap) {
    gsap.from("#formateur-hero .crumb, #formateur-hero .formateur-photo, #formateur-hero h1, #formateur-hero .formateur-title, #formateur-hero .formateur-stats, #formateur-hero .btn-cv", {
      y: 16, opacity: 0, duration: .55, stagger: .06, ease: "power2.out",
    });
    if (window.ScrollTrigger) {
      gsap.registerPlugin(ScrollTrigger);
      document.querySelectorAll(".formateur-wrap .panel").forEach((el, i) => {
        gsap.from(el, {
          scrollTrigger: { trigger: el, start: "top 90%" },
          y: 24, opacity: 0, duration: .5, delay: i * .04, ease: "power2.out",
        });
      });
    }
  }

  const thumbs = document.querySelectorAll(".attachment-card.is-image");
  const lightbox = document.getElementById("gallery-lightbox");
  if (thumbs.length && lightbox) {
    const lbImg = lightbox.querySelector("img");
    const urls = Array.from(thumbs).map((t) => t.dataset.full || t.href);
    let idx = 0;
    const show = (i) => { idx = (i + urls.length) % urls.length; lbImg.src = urls[idx]; };
    thumbs.forEach((t, i) => t.addEventListener("click", (e) => {
      e.preventDefault();
      show(i);
      lightbox.classList.add("open");
    }));
    lightbox.querySelector(".lb-close").addEventListener("click", () => lightbox.classList.remove("open"));
    lightbox.querySelector(".lb-prev").addEventListener("click", () => show(idx - 1));
    lightbox.querySelector(".lb-next").addEventListener("click", () => show(idx + 1));
    lightbox.addEventListener("click", (e) => { if (e.target === lightbox) lightbox.classList.remove("open"); });
    document.addEventListener("keydown", (e) => {
      if (!lightbox.classList.contains("open")) return;
      if (e.key === "Escape") lightbox.classList.remove("open");
      if (e.key === "ArrowRight") show(idx + 1);
      if (e.key === "ArrowLeft") show(idx - 1);
    });
  }
})();
