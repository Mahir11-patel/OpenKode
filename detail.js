const $ = (selector) => document.querySelector(selector);
const pagePath = window.location.pathname;
$('#year').textContent = new Date().getFullYear();
fetch(`/api/items?path=${encodeURIComponent(pagePath)}`)
  .then((response) => { if (!response.ok) throw new Error('Not found'); return response.json(); })
  .then((item) => {
    document.title = `${item.title} — Open-Kode`;
    $('#detail-kind').textContent = item.category;
    $('#detail-title').textContent = item.title;
    $('#detail-summary').textContent = item.summary;
    $('#detail-description').textContent = item.description;
    $('#detail-notes').textContent = item.notes;
    $('#detail-tags').replaceChildren(...item.tags.map((tag) => {
      const chip = document.createElement('span'); chip.textContent = tag; return chip;
    }));
    const download = $('#detail-download');
    download.href = `/api/download?id=${encodeURIComponent(item.download_id)}`;
    download.textContent = `${item.download_label} ↓`;
    const secondary = $('#detail-secondary');
    secondary.href = item.secondary_path;
    secondary.textContent = `${item.secondary_label} ↗`;
    $('#detail-loading').classList.add('hidden');
    $('#detail-content').classList.remove('hidden');
  })
  .catch(() => { $('#detail-loading').classList.add('hidden'); $('#detail-error').classList.remove('hidden'); });
