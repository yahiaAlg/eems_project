// catalog.html — branch → specialty AJAX cascade for the filter sidebar.
// Specialty options depend on the chosen branch, so they're fetched from
// /api/pages/specialties/?branch=<code> whenever the branch select changes
// (see pages/api_views.py SpecialtyViewSet). The other filters keep
// submitting the form directly (full reload); only this dependent select
// needs the AJAX round-trip.
(function () {
  const cfg = window.CATALOG_FILTERS || {};
  const branchSelect = document.getElementById('branchFilter');
  const specialtySelect = document.getElementById('specialtyFilter');
  if (!branchSelect || !specialtySelect || !cfg.specialtiesApiUrl) return;

  function setSpecialtyOptions(items, preselectCode) {
    specialtySelect.innerHTML = '';

    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = items.length
      ? 'كل تخصصات هذه الشعبة'
      : 'لا توجد تخصصات لهذه الشعبة';
    specialtySelect.appendChild(placeholder);

    items.forEach((sp) => {
      const opt = document.createElement('option');
      opt.value = sp.code;
      opt.textContent = `${sp.code} — ${sp.name}`;
      if (preselectCode && sp.code === preselectCode) opt.selected = true;
      specialtySelect.appendChild(opt);
    });

    specialtySelect.disabled = items.length === 0;
  }

  function loadSpecialties(branchCode, preselectCode) {
    specialtySelect.disabled = true;
    specialtySelect.innerHTML = '<option value="">جارٍ التحميل...</option>';

    fetch(`${cfg.specialtiesApiUrl}?branch=${encodeURIComponent(branchCode)}`, {
      headers: { Accept: 'application/json' },
    })
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => {
        const items = Array.isArray(data) ? data : (data.results || []);
        setSpecialtyOptions(items, preselectCode);
      })
      .catch(() => {
        specialtySelect.innerHTML = '<option value="">تعذّر تحميل التخصصات، حاول مجددا</option>';
        specialtySelect.disabled = true;
      });
  }

  branchSelect.addEventListener('change', () => {
    const opt = branchSelect.selectedOptions[0];
    const branchCode = opt ? opt.dataset.code : '';
    if (branchCode) {
      loadSpecialties(branchCode);
    } else {
      specialtySelect.innerHTML = '<option value="">اختر شعبة أولا</option>';
      specialtySelect.disabled = true;
    }
  });

  // Specialty is the last link in the cascade — applying it submits the
  // form like every other filter does on change.
  specialtySelect.addEventListener('change', () => {
    if (specialtySelect.form) specialtySelect.form.submit();
  });

  // Deep-links (e.g. from the nomenclature page's row/branch links, or a
  // reload with ?branch=&specialty= already in the URL) land here with a
  // branch pre-selected server-side — fetch its specialties and keep the
  // current selection instead of resetting the picker to empty.
  const initialOpt = branchSelect.selectedOptions[0];
  const initialCode = initialOpt ? initialOpt.dataset.code : '';
  if (initialCode) {
    loadSpecialties(initialCode, cfg.selectedSpecialty || '');
  }
})();
