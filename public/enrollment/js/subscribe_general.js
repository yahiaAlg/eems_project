// subscribe_general.html — branch -> specialty -> offering AJAX cascade.
// Each select is only populated once its parent has a value; the final
// pick's option carries the exact per-offering subscribe URL, so
// "متابعة" just navigates there — the real form (subscribe.html) takes
// over from that point on.
(function () {
  const cfg = window.SUBSCRIBE_GENERAL || {};
  const branchSelect = document.getElementById('branchSelect');
  const specialtySelect = document.getElementById('specialtySelect');
  const offeringSelect = document.getElementById('offeringSelect');
  const continueBtn = document.getElementById('continueBtn');
  const dot2 = document.getElementById('step-dot-2');
  const dot3 = document.getElementById('step-dot-3');
  if (!branchSelect || !specialtySelect || !offeringSelect || !continueBtn) return;

  function resetSelect(select, placeholder, disabled) {
    select.innerHTML = '';
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = placeholder;
    select.appendChild(opt);
    select.disabled = disabled;
  }

  function loadSpecialties(branchId) {
    resetSelect(specialtySelect, 'جارٍ التحميل...', true);
    resetSelect(offeringSelect, 'اختر تخصصا أولا', true);
    continueBtn.disabled = true;
    dot2.classList.remove('done');
    dot3.classList.remove('done');

    fetch(`${cfg.specialtiesApiUrl}?branch=${encodeURIComponent(branchId)}`, {
      headers: { Accept: 'application/json' },
    })
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => {
        const items = data.results || [];
        resetSelect(
          specialtySelect,
          items.length ? '-- اختر تخصصا --' : 'لا توجد تخصصات متاحة حاليا لهذه الشعبة',
          items.length === 0,
        );
        items.forEach((sp) => {
          const opt = document.createElement('option');
          opt.value = sp.code;
          opt.textContent = `${sp.code} — ${sp.name}`;
          specialtySelect.appendChild(opt);
        });
      })
      .catch(() => {
        resetSelect(specialtySelect, 'تعذّر تحميل التخصصات، حاول مجددا', true);
      });
  }

  function loadOfferings(specialtyCode) {
    resetSelect(offeringSelect, 'جارٍ التحميل...', true);
    continueBtn.disabled = true;
    dot3.classList.remove('done');

    fetch(`${cfg.offeringsApiUrl}?specialty=${encodeURIComponent(specialtyCode)}`, {
      headers: { Accept: 'application/json' },
    })
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => {
        const items = data.results || [];
        resetSelect(
          offeringSelect,
          items.length ? '-- اختر تكوينا --' : 'لا توجد دورات مفتوحة حاليا لهذا التخصص',
          items.length === 0,
        );
        items.forEach((of) => {
          const opt = document.createElement('option');
          opt.value = of.subscribe_url;
          const seatsNote = of.seats_remaining > 0 ? `${of.seats_remaining} مقعد متبقي` : 'قائمة انتظار';
          opt.textContent = `${of.title} — ${of.session_name} (${seatsNote})`;
          offeringSelect.appendChild(opt);
        });
      })
      .catch(() => {
        resetSelect(offeringSelect, 'تعذّر تحميل التكوينات، حاول مجددا', true);
      });
  }

  branchSelect.addEventListener('change', () => {
    if (branchSelect.value) {
      loadSpecialties(branchSelect.value);
    } else {
      resetSelect(specialtySelect, 'اختر شعبة أولا', true);
      resetSelect(offeringSelect, 'اختر تخصصا أولا', true);
      continueBtn.disabled = true;
      dot2.classList.remove('done');
      dot3.classList.remove('done');
    }
  });

  specialtySelect.addEventListener('change', () => {
    if (specialtySelect.value) {
      dot2.classList.add('done');
      loadOfferings(specialtySelect.value);
    } else {
      resetSelect(offeringSelect, 'اختر تخصصا أولا', true);
      continueBtn.disabled = true;
      dot3.classList.remove('done');
    }
  });

  offeringSelect.addEventListener('change', () => {
    continueBtn.disabled = !offeringSelect.value;
    if (offeringSelect.value) dot3.classList.add('done');
  });

  continueBtn.addEventListener('click', () => {
    if (offeringSelect.value) window.location.href = offeringSelect.value;
  });
})();
