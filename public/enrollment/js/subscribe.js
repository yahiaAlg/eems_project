// subscribe.html — form entrance animation.
(function () {
  gsap.from("#anim-title", { y: 16, opacity: 0, duration: .55, ease: "power2.out" });
  gsap.from("#anim-summary", { x: 24, opacity: 0, duration: .6, delay: .1, ease: "power2.out" });
  gsap.from("#anim-form", { y: 20, opacity: 0, duration: .6, delay: .05, ease: "power2.out" });
})();
