// subscribe.html — form entrance animation.
(function () {
  gsap.from("#anim-title", { y: 16, opacity: 0, duration: .55, ease: "power2.out" });
  gsap.from("#anim-summary", { x: 24, opacity: 0, duration: .6, delay: .1, ease: "power2.out" });
  gsap.from("#anim-form", { y: 20, opacity: 0, duration: .6, delay: .05, ease: "power2.out" });
})();

// subscribe.html — show individual fields (name/birth date/education...) or
// enterprise fields (company/responsible contact...) depending on the
// "نوع المسجّل" choice, same toggle pattern as accounts/register.html.
(function () {
  const form = document.getElementById("subscribeForm");
  if (!form) return;
  const radios = form.querySelectorAll('input[name="client_type"]');
  const fields = form.querySelectorAll(".login-field");
  function sync() {
    const checked = form.querySelector('input[name="client_type"]:checked');
    const type = checked ? checked.value : "individual";
    fields.forEach((f) => {
      f.style.display = f.dataset.type === type ? "" : "none";
    });
  }
  radios.forEach((r) => r.addEventListener("change", sync));
  sync();
})();
