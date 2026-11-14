const $ = (selector) => document.querySelector(selector);
const authPanel = $('#auth-panel');
const dashboard = $('#dashboard');
const loginForm = $('#login-form');
const registerForm = $('#register-form');
const contentForm = $('#content-form');
const ownerEmail = 'mahir31891@gmail.com';

function message(target, text, error = false) {
  target.textContent = text;
  target.classList.toggle('error', error);
}

async function request(path, options = {}) {
  const response = await fetch(path, {credentials: 'same-origin', ...options});
  let result;
  try { result = await response.json(); } catch { result = {}; }
  if (!response.ok) throw new Error(result.error || 'The request could not be completed.');
  return result;
}

function showAuthMode(mode) {
  const login = mode === 'login';
  loginForm.classList.toggle('hidden', !login);
  registerForm.classList.toggle('hidden', login);
  $('#login-tab').classList.toggle('active', login);
  $('#register-tab').classList.toggle('active', !login);
  $('#login-tab').setAttribute('aria-selected', String(login));
  $('#register-tab').setAttribute('aria-selected', String(!login));
  $('#auth-title').textContent = login ? 'Welcome back' : 'Create your account';
  message($('#auth-message'), '');
}

function fillContent(content) {
  $('#edit-hero-lead').value = content.hero_lead;
  $('#edit-hero-accent').value = content.hero_accent;
  $('#edit-hero-description').value = content.hero_description;
  $('#edit-about-heading').value = `${content.about_heading_first}\n${content.about_heading_second}`;
  $('#edit-about-description').value = content.about_description;
  $('#edit-footer-description').value = content.footer_description;
}

function showDashboard(account) {
  authPanel.classList.add('hidden');
  dashboard.classList.remove('hidden');
  $('#sign-out').classList.remove('hidden');
  $('#welcome-title').textContent = `Welcome, ${account.display_name}`;
  $('#welcome-email').textContent = account.email;
  $('#profile-name').textContent = account.display_name;
  $('#profile-email').textContent = account.email;
  const isAdmin = account.is_admin === true || account.role === 'admin';
  $('#account-role').textContent = isAdmin ? 'OPEN-KODE COMPANY ADMIN' : 'OPEN-KODE ACCOUNT';
  $('#account-access').textContent = isAdmin ? 'Permanent owner access' : 'Account active';
  $('#admin-tools').classList.toggle('hidden', !isAdmin);
  $('#user-notice').classList.toggle('hidden', isAdmin);
  if (isAdmin) {
    loadContent();
    loadProjects();
    loadApiKeys();
    loadAccounts();
  }
}

async function loadContent() {
  try { fillContent(await request('/api/content')); }
  catch (error) { message($('#save-message'), error.message, true); }
}

function setProjectStats(items) {
  $('#stat-items').textContent = items.length;
  $('#stat-models').textContent = items.filter((item) => item.categories.includes('ai')).length;
  $('#stat-apps').textContent = items.filter((item) => item.categories.includes('app')).length;
  const list = $('#console-projects');
  list.replaceChildren(...items.map((item) => {
    const row = document.createElement('div'); row.className = 'console-project';
    const icon = document.createElement('span'); icon.className = 'project-icon'; icon.textContent = item.icon;
    const info = document.createElement('span');
    const title = document.createElement('b'); title.textContent = item.name;
    const kind = document.createElement('small'); kind.textContent = item.category_label;
    info.append(title, kind);
    const status = document.createElement('i'); status.className = 'project-status'; status.setAttribute('aria-label', 'Published');
    row.append(icon, info, status); return row;
  }));
}

async function loadProjects() {
  try {
    const {items} = await request('/api/catalog');
    setProjectStats(items);
  } catch {
    $('#console-projects').innerHTML = '<p class="console-empty">The project list could not be loaded.</p>';
  }
}

function renderApiKeys(keys) {
  const list = $('#api-keys-list');
  $('#stat-api-keys').textContent = keys.filter((key) => !key.revoked_at && (key.is_admin || !key.paid_until || key.paid_until >= new Date().toISOString().slice(0, 10))).length;
  if (!keys.length) {
    list.innerHTML = '<p class="console-empty">No KODE.MINI API keys have been issued yet.</p>';
    return;
  }
  list.replaceChildren(...keys.map((key) => {
    const row = document.createElement('article'); row.className = `api-key-row${key.revoked_at ? ' revoked' : ''}`;
    const detail = document.createElement('div'); detail.className = 'api-key-detail';
    const title = document.createElement('b'); title.textContent = key.label;
    const meta = document.createElement('small'); meta.textContent = `${key.email} · ${key.key_prefix}… · ${key.is_admin ? 'permanent owner key' : `active through ${key.paid_until}`}`;
    const usage = document.createElement('small'); usage.textContent = key.revoked_at ? `Revoked ${new Date(key.revoked_at).toLocaleDateString()}` : `Created ${new Date(key.created_at).toLocaleDateString()}${key.last_used_at ? ` · used ${new Date(key.last_used_at).toLocaleString()}` : ' · never used'}`;
    detail.append(title, meta, usage);
    if (!key.revoked_at) {
      const revoke = document.createElement('button'); revoke.className = 'button button-outline key-revoke'; revoke.type = 'button'; revoke.textContent = 'Revoke'; revoke.dataset.revokeId = key.id;
      row.append(detail, revoke);
    } else {
      const tag = document.createElement('span'); tag.className = 'key-revoked-tag'; tag.textContent = 'REVOKED';
      row.append(detail, tag);
    }
    return row;
  }));
}

async function loadApiKeys() {
  try {
    const {keys} = await request('/api/admin/model-keys');
    renderApiKeys(keys);
  } catch (error) {
    $('#api-keys-list').textContent = error.message;
    $('#api-keys-list').classList.add('console-error-box');
  }
}

async function loadAccounts() {
  const list = $('#accounts-list');
  try {
    const {accounts} = await request('/api/admin/accounts');
    $('#account-count').textContent = accounts.length;
    if (!accounts.length) { list.innerHTML = '<p class="console-empty">No accounts have been registered.</p>'; return; }
    list.replaceChildren(...accounts.map((account) => {
      const row = document.createElement('article'); row.className = 'saved-account-row';
      const identity = document.createElement('div');
      const name = document.createElement('b'); name.textContent = account.display_name;
      const email = document.createElement('small'); email.textContent = account.email;
      identity.append(name, email);
      const info = document.createElement('div'); info.className = 'saved-account-meta';
      const role = document.createElement('span'); role.textContent = account.role === 'admin' ? 'COMPANY ADMIN' : 'ACCOUNT';
      const date = document.createElement('small'); date.textContent = `Joined ${new Date(account.created_at).toLocaleDateString()}${account.last_login_at ? ` · last sign-in ${new Date(account.last_login_at).toLocaleDateString()}` : ''}`;
      info.append(role, date); row.append(identity, info); return row;
    }));
  } catch (error) { list.textContent = error.message; list.classList.add('console-error-box'); }
}

async function loadSession() {
  try {
    const state = await request('/api/auth/session');
    if (state.authenticated) showDashboard(state.account);
  } catch (error) { message($('#auth-message'), error.message || 'Could not connect to the local Open-Kode server.', true); }
}

$('#login-tab').addEventListener('click', () => showAuthMode('login'));
$('#register-tab').addEventListener('click', () => showAuthMode('register'));

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const status = $('#auth-message'); message(status, 'Signing in…');
  try {
    const result = await request('/api/auth/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({email: $('#login-email').value.trim(), password: $('#login-password').value})});
    showDashboard(result.account);
    $('#login-password').value = '';
    message(status, '');
  } catch (error) { message(status, error.message, true); }
});

registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const password = $('#register-password').value;
  if (password !== $('#register-confirm').value) { message($('#auth-message'), 'The passwords do not match.', true); return; }
  const status = $('#auth-message'); message(status, 'Creating your account…');
  try {
    const result = await request('/api/auth/register', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({display_name: $('#register-name').value.trim(), email: $('#register-email').value.trim(), password})});
    registerForm.reset();
    showDashboard(result.account);
    message(status, '');
  } catch (error) { message(status, error.message, true); }
});

contentForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const heading = $('#edit-about-heading').value.split('\n').map((line) => line.trim()).filter(Boolean);
  if (heading.length !== 2) { message($('#save-message'), 'Enter the about heading on exactly two lines.', true); return; }
  const content = {
    hero_lead: $('#edit-hero-lead').value.trim(), hero_accent: $('#edit-hero-accent').value.trim(),
    hero_description: $('#edit-hero-description').value.trim(), about_heading_first: heading[0],
    about_heading_second: heading[1], about_description: $('#edit-about-description').value.trim(),
    footer_description: $('#edit-footer-description').value.trim()
  };
  message($('#save-message'), 'Saving…');
  try { await request('/api/admin/content', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(content)}); message($('#save-message'), 'Saved. The homepage now shows your updates.'); }
  catch (error) { message($('#save-message'), error.message, true); }
});

$('#key-email').addEventListener('input', () => {
  const owner = $('#key-email').value.trim().toLowerCase() === ownerEmail;
  $('#key-expiry').required = !owner;
  $('#key-expiry').disabled = owner;
  if (owner) $('#key-expiry').value = '';
});

$('#api-key-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const email = $('#key-email').value.trim();
  const owner = email.toLowerCase() === ownerEmail;
  message($('#key-message'), 'Creating key…');
  $('#key-reveal').classList.add('hidden');
  try {
    const result = await request('/api/admin/model-keys', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({email, label: $('#key-label').value.trim(), paid_until: owner ? '' : $('#key-expiry').value})});
    $('#new-key-value').textContent = result.api_key;
    $('#key-reveal').classList.remove('hidden');
    message($('#key-message'), 'Key created. Copy it now; it will not be shown again.');
    await loadApiKeys();
  } catch (error) { message($('#key-message'), error.message, true); }
});

$('#api-keys-list').addEventListener('click', async (event) => {
  const button = event.target.closest('[data-revoke-id]');
  if (!button || !confirm('Revoke this KODE.MINI API key? The key will stop working immediately.')) return;
  button.disabled = true;
  try {
    await request('/api/admin/model-keys/revoke', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: button.dataset.revokeId})});
    message($('#key-message'), 'API key revoked.');
    await loadApiKeys();
  } catch (error) { button.disabled = false; message($('#key-message'), error.message, true); }
});

$('#copy-key').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText($('#new-key-value').textContent);
    message($('#key-message'), 'API key copied to clipboard. Save it somewhere private.');
  } catch { message($('#key-message'), 'Copy failed. Select the key above and copy it manually.', true); }
});

$('#password-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  message($('#password-message'), 'Updating password…');
  try {
    await request('/api/account/password', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({current_password: $('#current-password').value, new_password: $('#new-password').value})});
    event.currentTarget.reset();
    message($('#password-message'), 'Password updated.');
  } catch (error) { message($('#password-message'), error.message, true); }
});

$('#sign-out').addEventListener('click', async () => {
  try { await request('/api/auth/logout', {method: 'POST'}); } catch { /* Clear the local view if the server is already unavailable. */ }
  dashboard.classList.add('hidden'); authPanel.classList.remove('hidden'); $('#sign-out').classList.add('hidden');
  loginForm.reset(); $('#login-email').value = ownerEmail;
  message($('#auth-message'), 'You are signed out.');
  showAuthMode('login');
});

$('#year').textContent = new Date().getFullYear();
$('#key-email').dispatchEvent(new Event('input'));
loadSession();
