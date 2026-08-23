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
      const [code, name, branch] = row;
      const matchBranch = !branchQ || branch === branchQ;
      const matchSearch = !searchQ ||
        code.toLowerCase().includes(searchQ.toLowerCase()) ||
        name.includes(searchQ) ||
        branch.includes(searchQ);
      if (matchBranch && matchSearch) {
        count++;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="nomen-num">${count}</td>
          <td><span class="nomen-code">${highlight(code, searchQ)}</span></td>
          <td class="nomen-name">${highlight(name, searchQ)}</td>
          <td><span class="nomen-branch-badge">${highlight(branch, searchQ)}</span></td>
        `;
        if (catalogUrl) {
          tr.style.cursor = 'pointer';
          tr.title = 'عرض تكوينات هذا التخصص';
          tr.addEventListener('click', () => {
            window.location.href = `${catalogUrl}?specialty=${encodeURIComponent(code)}`;
          });
        }
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
