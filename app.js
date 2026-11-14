const $ = (selector) => document.querySelector(selector);
const API = '/api';
const catalogGrid = $('#catalog-grid');

function setMessage(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle('error', isError);
}

function applyContent(content) {
  $('[data-content="hero_lead"]').textContent = content.hero_lead;
  $('[data-content="hero_accent"]').textContent = content.hero_accent;
  $('[data-content="hero_description"]').textContent = content.hero_description;
  $('[data-content="about_heading"]').childNodes[0].textContent = content.about_heading_first;
  $('[data-content="about_heading"] span').textContent = content.about_heading_second;
  $('[data-content="about_description"]').textContent = content.about_description;
  $('[data-content="footer_description"]').textContent = content.footer_description;
}


function createCatalogCard(item) {
  const article = document.createElement('article');
  article.className = 'catalog-card';
  article.dataset.categories = item.categories.join(' ');
  const top = document.createElement('div'); top.className = 'catalog-top';
  const icon = document.createElement('span'); icon.className = 'catalog-icon'; icon.textContent = item.icon;
  const category = document.createElement('span'); category.className = 'catalog-category'; category.textContent = item.category_label;
  top.append(icon, category);
  const title = document.createElement('h3'); title.textContent = item.name;
  const description = document.createElement('p'); description.textContent = item.description;
  const meta = document.createElement('div'); meta.className = 'catalog-meta';
  item.tags.forEach((tag) => { const chip = document.createElement('span'); chip.textContent = tag; meta.append(chip); });
  const actions = document.createElement('div'); actions.className = 'catalog-actions';
  const download = document.createElement('a'); download.href = `/api/download?id=${encodeURIComponent(item.download_id)}`; download.textContent = item.download_label;
  const details = document.createElement('a'); details.className = 'catalog-details'; details.href = item.detail_path; details.textContent = 'View details ↗';
  actions.append(download, details);
  article.append(top, title, description, meta, actions);
  return article;
}

async function loadPublicData() {
  try {
    const [contentResponse, catalogResponse] = await Promise.all([fetch(`${API}/content`), fetch(`${API}/catalog`)]);
    if (!contentResponse.ok || !catalogResponse.ok) throw new Error('Could not load site information.');
    applyContent(await contentResponse.json());
    const catalog = await catalogResponse.json();
    catalogGrid.replaceChildren(...catalog.items.map(createCatalogCard));
    setupFilters();
  } catch (error) {
    const message = document.createElement('p');
    message.className = 'empty-card';
    message.textContent = 'The project library could not load. Refresh the page or try again shortly.';
    catalogGrid.replaceChildren(message);
  }
}

function setupFilters() {
  document.querySelectorAll('.filter').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.filter').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      const filter = button.dataset.filter;
      document.querySelectorAll('.catalog-card').forEach((card) => {
        card.hidden = filter !== 'all' && !card.dataset.categories.split(' ').includes(filter);
      });
    });
  });
}

const menuButton = $('.menu-toggle');
const nav = $('.desktop-nav');
menuButton.addEventListener('click', () => {
  const isOpen = nav.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', String(isOpen));
  menuButton.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
});
nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
  nav.classList.remove('open'); menuButton.setAttribute('aria-expanded', 'false');
}));
$('#year').textContent = new Date().getFullYear();
loadPublicData();



