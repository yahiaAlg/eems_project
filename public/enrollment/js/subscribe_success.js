// subscribe_success.html — entrance animation + confetti burst (no external assets).
(function () {
  const tl = gsap.timeline();
  tl.from(".icon-badge", { scale: 0, opacity: 0, duration: .5, ease: "back.out(1.7)" })
    .from("h1, p, .steps li, a.cta", { y: 14, opacity: 0, duration: .4, stagger: .08, ease: "power2.out" }, "-=.15");

  const colors = ["#f59e0b", "#10b981", "#60a5fa", "#fbbf24"];
  const panel = document.getElementById("success-panel");
  for (let i = 0; i < 24; i++) {
    const el = document.createElement("div");
    el.className = "confetti";
    el.style.background = colors[i % colors.length];
    el.style.left = 50 + (Math.random() * 40 - 20) + "%";
    el.style.top = "20%";
    panel.appendChild(el);
    gsap.to(el, {
      opacity: 1, y: 200 + Math.random() * 120, x: (Math.random() * 160 - 80),
      rotation: Math.random() * 360, duration: 1.4 + Math.random(), delay: .3 + i * .02,
      ease: "power1.out",
      onComplete: () => gsap.to(el, { opacity: 0, duration: .4 }),
    });
  }
})();
