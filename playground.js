const $ = (selector) => document.querySelector(selector);
const form = $('#chat-form');
const input = $('#chat-input');
const messages = $('#live-messages');
const sendButton = $('#send-button');
const status = $('#model-status');
let userId;
try {
  userId = localStorage.getItem('openkode-demo-id');
  if (!userId) {
    userId = crypto.randomUUID ? crypto.randomUUID() : `demo-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem('openkode-demo-id', userId);
  }
} catch { userId = `demo-${Date.now()}-${Math.random().toString(36).slice(2)}`; }

function addMessage(text, role) {
  const row = document.createElement('div'); row.className = `chat-row ${role}-row`;
  if (role === 'assistant') {
    const avatar = document.createElement('img'); avatar.className = 'chat-avatar'; avatar.src = '/assets/favicon.png'; avatar.alt = ''; row.append(avatar);
  }
  const bubble = document.createElement('p'); bubble.textContent = text; row.append(bubble); messages.append(row); messages.scrollTop = messages.scrollHeight;
  return row;
}

async function sendMessage(text) {
  const message = text.trim();
  if (!message || sendButton.disabled) return;
  addMessage(message, 'user'); input.value = ''; sendButton.disabled = true; status.textContent = 'Thinking…';
  const waiting = addMessage('KODE.MINI is preparing a response…', 'assistant'); waiting.classList.add('waiting-row');
  try {
    const response = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message, user_id:userId})});
    const result = await response.json();
    waiting.remove();
    if (!response.ok) throw new Error(result.error || 'The model could not respond.');
    addMessage(result.response || 'The model returned an empty response.', 'assistant');
    status.textContent = `Intent: ${result.intent}`;
  } catch (error) {
    waiting.remove(); addMessage(error.message || 'Could not connect to the Python model.', 'assistant'); status.textContent = 'Unavailable';
  } finally { sendButton.disabled = false; input.focus(); }
}

form.addEventListener('submit', (event) => { event.preventDefault(); sendMessage(input.value); });
document.querySelectorAll('[data-prompt]').forEach((button) => button.addEventListener('click', () => sendMessage(button.dataset.prompt)));
$('#year').textContent = new Date().getFullYear();
