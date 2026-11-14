import siteData from './site-data.json' with {type: 'json'};
import {getContent, json} from './shared.mjs';

const DOWNLOADS = {
  'kode-mini-python': '/downloads/kode_mini.py',
  'kode-mini-readme': '/downloads/KODE-MINI-README.md',
  'openkode-license': '/downloads/LICENSE',
  'openkode-source': '/downloads/openkode-source.zip',
  'app-clawd': '/downloads/Clawd.exe',
  'app-ganesha': '/downloads/Ganesha.exe',
  'app-kode': '/downloads/Kode.exe',
  'app-minux': '/downloads/Minux.exe'
};

const LOCAL_BACKEND = 'This feature requires the local Python server. Netlify serves the static website but does not run the KODE.MINI Python engine or its account database.';

export default async (request) => {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method.toUpperCase();

  try {
    if (path === '/api/content' && method === 'GET') return json(await getContent());
    if (path === '/api/catalog' && method === 'GET') return json({items: siteData.catalog});
    if (path === '/api/items' && method === 'GET') {
      const slug = siteData.detail_routes[url.searchParams.get('path') || ''];
      const detail = siteData.details[slug];
      return detail ? json(detail) : json({error: 'Item not found.'}, 404);
    }
    if (path === '/api/download' && method === 'GET') {
      const location = DOWNLOADS[url.searchParams.get('id') || ''];
      return location ? Response.redirect(new URL(location, url.origin), 302) : json({error: 'This public download is not available.'}, 404);
    }
    if (path === '/api/admin/session' || path === '/api/admin/content' || path === '/api/admin/accounts' || path.startsWith('/api/admin/model-keys') || path.startsWith('/v1/')) {
      return json({error: LOCAL_BACKEND}, 503);
    }
    if (path === '/api/chat' && method === 'POST') return json({error: LOCAL_BACKEND}, 503);
    return json({error: 'Page not found.'}, 404);
  } catch (error) {
    console.error('Open-Kode API request failed:', error?.message || 'unknown error');
    return json({error: 'The Open-Kode service is temporarily unavailable.'}, 503);
  }
};

export const config = {
  path: ['/api/content', '/api/catalog', '/api/items', '/api/admin/session', '/api/admin/content', '/api/admin/accounts', '/api/admin/model-keys', '/api/admin/model-keys/revoke', '/api/download', '/api/chat', '/v1/models', '/v1/chat/completions']
};
