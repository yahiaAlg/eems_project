// catalog.html — hero/card entrance animations + seat-bar fill (GSAP).
(function () {
  gsap.registerPlugin(ScrollTrigger);

  gsap.from("#catalog-hero .catalog-badge, #catalog-hero h1, #catalog-hero p, #catalog-hero .stat-pill", {
    y: 18, opacity: 0, duration: .6, stagger: .08, ease: "power2.out",
  });

  document.querySelectorAll(".offer-item").forEach((card, i) => {
    gsap.from(card, {
      scrollTrigger: { trigger: card, start: "top 92%" },
      y: 26, opacity: 0, duration: .55, delay: (i % 3) * .05, ease: "power2.out",
    });
  });

  document.querySelectorAll(".seats-bar span").forEach((bar) => {
    ScrollTrigger.create({
      trigger: bar,
      start: "top 95%",
      onEnter: () => gsap.to(bar, { width: bar.dataset.fill + "%", duration: 1.1, ease: "power2.out" }),
      once: true,
    });
  });

  // Grid / list view toggle
  const grid = document.getElementById("offer-grid");
  const viewButtons = document.querySelectorAll("[data-view]");
  if (grid && viewButtons.length) {
    const stored = localStorage.getItem("catalogView");
    if (stored === "list") grid.classList.add("view-list");
    viewButtons.forEach((btn) => {
      if (btn.dataset.view === (stored || "grid")) btn.classList.add("active");
      btn.addEventListener("click", () => {
        viewButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        grid.classList.toggle("view-list", btn.dataset.view === "list");
        localStorage.setItem("catalogView", btn.dataset.view);
      });
    });
  }
})();
