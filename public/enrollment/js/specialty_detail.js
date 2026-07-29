// specialty_detail.html — hero/panel entrance animations, seat-bar fill, hash-scroll to comments/enquiry.
(function () {
  gsap.registerPlugin(ScrollTrigger);

  gsap.from("#detail-hero .crumb, #detail-hero .hero-code, #detail-hero h1, #detail-hero .hero-sub", {
    y: 16, opacity: 0, duration: .55, stagger: .07, ease: "power2.out",
  });

  document.querySelectorAll(".reveal-item").forEach((el, i) => {
    gsap.from(el, {
      scrollTrigger: { trigger: el, start: "top 90%" },
      y: 24, opacity: 0, duration: .5, delay: i * .04, ease: "power2.out",
    });
  });

  document.querySelectorAll(".seats-bar span").forEach((bar) => {
    ScrollTrigger.create({
      trigger: bar, start: "top 95%", once: true,
      onEnter: () => gsap.to(bar, { width: bar.dataset.fill + "%", duration: 1.2, ease: "power2.out" }),
    });
  });

  // Smooth-scroll to #comments / #enquiry if the URL asks for it (e.g. after a POST redirect)
  if (location.hash === "#comments" || location.hash === "#enquiry") {
    const target = document.querySelector(location.hash);
    if (target) setTimeout(() => target.scrollIntoView({ behavior: "smooth", block: "start" }), 200);
  }

  // Gallery lightbox (used when the fiche technique includes secondary images)
  const thumbs = document.querySelectorAll(".gallery-thumb");
  const lightbox = document.getElementById("gallery-lightbox");
  if (thumbs.length && lightbox) {
    const lbImg = lightbox.querySelector("img");
    const urls = Array.from(thumbs).map((t) => t.dataset.full || t.querySelector("img").src);
    let idx = 0;
    const show = (i) => { idx = (i + urls.length) % urls.length; lbImg.src = urls[idx]; };
    thumbs.forEach((t, i) => t.addEventListener("click", () => { show(i); lightbox.classList.add("open"); }));
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
