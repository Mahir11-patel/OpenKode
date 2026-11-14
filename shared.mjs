import {getStore} from '@netlify/blobs';

export const SITE_STORE = getStore({name: 'openkode-site-content', consistency: 'strong'});

export function json(payload, status = 200, headers = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...headers}
  });
}

export function originAllowed(request) {
  const origin = request.headers.get('origin');
  if (!origin) return true;
  try { return new URL(origin).origin === new URL(request.url).origin; }
  catch { return false; }
}

export async function readJson(request) {
  const raw = await request.text();
  if (!raw || new TextEncoder().encode(raw).byteLength > 65536) throw new Error('Request body is empty or too large.');
  try {
    const value = JSON.parse(raw);
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error();
    return value;
  } catch { throw new Error('Request must contain a valid JSON object.'); }
}

const DEFAULT_CONTENT = {
  hero_lead: 'Build openly.',
  hero_accent: 'Go further.',
  hero_description: 'Open-Kode brings code, useful AI, and thoughtful software together so more people can turn ideas into things that work.',
  about_heading_first: 'Good ideas grow',
  about_heading_second: 'when they’re shared.',
  about_description: 'Open-Kode is a home for practical software and AI projects. Browse the source, learn how each piece works, and build something of your own.',
  footer_description: 'Useful software and AI,\nbuilt to be shared.'
};

export async function getContent() {
  const saved = await SITE_STORE.get('homepage-copy', {type: 'json', consistency: 'strong'});
  return saved && typeof saved === 'object' ? {...DEFAULT_CONTENT, ...saved} : {...DEFAULT_CONTENT};
}
