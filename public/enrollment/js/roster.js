// enrollment_roster.html — dynamic add/remove rows for the company roster
// formset (TODO 10.2.4), with no per-row reload: the whole table is one
// <form>, submitted once. Uses Django's standard management-form pattern
// (TOTAL_FORMS / an `empty_form` template with `__prefix__` placeholders).
(function () {
  const table = document.getElementById('roster-table');
  if (!table) return;

  const totalFormsInput = document.querySelector('#id_roster-TOTAL_FORMS');
  const rowsBody = document.getElementById('roster-rows');
  const emptyRowTemplate = document.getElementById('empty-row-template');
  const addBtn = document.getElementById('roster-add-row');
  const maxRows = parseInt(table.dataset.maxRows || '0', 10);
  const form = document.getElementById('roster-form');

  function currentRowCount() {
    return rowsBody.querySelectorAll('tr.roster-row').length;
  }

  function updateAddButtonState() {
    if (!addBtn) return;
    const atCap = maxRows > 0 && currentRowCount() >= maxRows;
    addBtn.disabled = atCap;
    addBtn.title = atCap
      ? `تم بلوغ الحد الأقصى لعدد المشاركين (${maxRows}).`
      : '';
  }

  function addRow() {
    if (!emptyRowTemplate || !totalFormsInput) return;
    const index = parseInt(totalFormsInput.value, 10);
    if (maxRows > 0 && currentRowCount() >= maxRows) return;

    const html = emptyRowTemplate.innerHTML.replace(/__prefix__/g, String(index));
    const wrapper = document.createElement('tbody');
    wrapper.innerHTML = html.trim();
    const row = wrapper.querySelector('tr');
    row.classList.add('roster-row');
    rowsBody.appendChild(row);

    totalFormsInput.value = String(index + 1);
    updateAddButtonState();
    const firstInput = row.querySelector('input[type="text"], input:not([type="hidden"])');
    if (firstInput) firstInput.focus();
  }

  function removeRow(row) {
    const idInput = row.querySelector('input[id$="-id"]');
    const isExistingRow = idInput && idInput.value;

    if (isExistingRow) {
      // Existing DB row: flag DELETE and hide, don't rip it out of the
      // DOM — Django's formset needs the DELETE=on value in the POST to
      // actually remove it server-side (see enrollment/views.py).
      const deleteInput = row.querySelector('input[id$="-DELETE"]');
      if (deleteInput) deleteInput.checked = true;
      row.style.display = 'none';
    } else {
      // Still-unsaved new row: just drop it and shrink TOTAL_FORMS so the
      // remaining rows stay a contiguous 0..N-1 index range.
      row.remove();
      if (totalFormsInput) {
        totalFormsInput.value = String(Math.max(currentRowCount(), 0));
      }
    }
    updateAddButtonState();
  }

  function validateBeforeSubmit(event) {
    let firstInvalidRow = null;
    rowsBody.querySelectorAll('tr.roster-row').forEach((row) => {
      if (row.style.display === 'none') return; // already marked for deletion
      const deleteInput = row.querySelector('input[id$="-DELETE"]');
      if (deleteInput && deleteInput.checked) return;

      const firstName = row.querySelector('input[id$="-first_name"]');
      const lastName = row.querySelector('input[id$="-last_name"]');
      const bothBlank = !(firstName && firstName.value.trim()) && !(lastName && lastName.value.trim());
      if (bothBlank) return; // untouched extra row — Django ignores it too

      const missingFirst = firstName && !firstName.value.trim();
      const missingLast = lastName && !lastName.value.trim();
      row.classList.toggle('roster-row-error', Boolean(missingFirst || missingLast));
      if ((missingFirst || missingLast) && !firstInvalidRow) firstInvalidRow = row;
    });

    if (firstInvalidRow) {
      event.preventDefault();
      firstInvalidRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  if (addBtn) addBtn.addEventListener('click', addRow);

  rowsBody.addEventListener('click', (event) => {
    const removeBtn = event.target.closest('.roster-remove-row');
    if (!removeBtn) return;
    event.preventDefault();
    removeRow(removeBtn.closest('tr'));
  });

  if (form) form.addEventListener('submit', validateBeforeSubmit);

  updateAddButtonState();
})();
