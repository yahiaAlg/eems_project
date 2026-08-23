// nomenclature.html — search/filter logic for the specialty table.
// Expects a <script type="application/json" id="specialties-data"> element (json_script tag).
(function () {
  const dataEl = document.getElementById('specialties-data');
  if (!dataEl) return;
  const data = JSON.parse(dataEl.textContent);

  const tbody = document.getElementById('tableBody');
  const searchInput = document.getElementById('searchInput');
  const branchFilter = document.getElementById('branchFilter');
  const visibleCount = document.getElementById('visibleCount');
  const totalCount = document.getElementById('totalCount');
  const noResults = document.getElementById('noResults');

  totalCount.textContent = data.length;
  const catalogUrl = window.CATALOG_URL || '';

  function highlight(text, query) {
    if (!query) return text;
    const re = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(re, '<mark>$1</mark>');
  }

  function render(searchQ, branchQ) {
    tbody.innerHTML = '';
    let count = 0;
    data.forEach((row) => {
      const [code, name, branch, branchCode, branchId] = row;
      const matchBranch = !branchQ || branch === branchQ;
      const matchSearch = !searchQ ||
        code.toLowerCase().includes(searchQ.toLowerCase()) ||
        name.includes(searchQ) ||
        branch.includes(searchQ);
      if (matchBranch && matchSearch) {
        count++;
        const tr = document.createElement('tr');

        // Row link: filters the catalog by this branch + this specialty.
        // Branch pill link: filters the catalog by the branch alone.
        // Both are real <a> tags (hover cursor, ctrl/cmd-click new tab,
        // crawlable) — the row link is stretched over the whole <tr> via
        // CSS (.stretched-link), the branch pill sits above it (z-index)
        // so it stays its own independent click target.
        let rowHref = '';
        let branchHref = '';
        if (catalogUrl) {
          const rowParams = new URLSearchParams();
          if (branchId) rowParams.set('branch', branchId);
          rowParams.set('specialty', code);
          rowHref = `${catalogUrl}?${rowParams.toString()}`;

          const branchParams = new URLSearchParams();
          if (branchId) branchParams.set('branch', branchId);
          branchHref = `${catalogUrl}?${branchParams.toString()}`;
        }

        tr.innerHTML = `
          <td class="nomen-num">${count}</td>
          <td>
            ${rowHref
              ? `<a class="nomen-row-link stretched-link" href="${rowHref}" title="عرض تكوينات هذا التخصص"><span class="nomen-code">${highlight(code, searchQ)}</span></a>`
              : `<span class="nomen-code">${highlight(code, searchQ)}</span>`}
          </td>
          <td class="nomen-name">${highlight(name, searchQ)}</td>
          <td>
            ${branchHref
              ? `<a class="nomen-branch-badge-link" href="${branchHref}" title="عرض كل تكوينات هذه الشعبة"><span class="nomen-branch-badge">${highlight(branch, searchQ)}</span></a>`
              : `<span class="nomen-branch-badge">${highlight(branch, searchQ)}</span>`}
          </td>
        `;
        tbody.appendChild(tr);
      }
    });
    visibleCount.textContent = count;
    noResults.style.display = count === 0 ? 'block' : 'none';
  }

  render('', '');

  searchInput.addEventListener('input', () => render(searchInput.value.trim(), branchFilter.value));
  branchFilter.addEventListener('change', () => render(searchInput.value.trim(), branchFilter.value));

  // Deep-link support: #ACP scrolls/filters to that branch code if present in URL hash
  if (window.location.hash) {
    const code = window.location.hash.replace('#', '');
    const match = data.find(row => row[3] === code);
    if (match) {
      branchFilter.value = match[2];
      render('', match[2]);
    }
  }
})();
