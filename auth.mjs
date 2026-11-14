import {json, originAllowed} from './shared.mjs';

const localBackendMessage = 'Email/password accounts and KODE.MINI keys are stored by the local Python server. Run python server.py to use the console.';

export default async (request) => {
  const {pathname} = new URL(request.url);
  const method = request.method.toUpperCase();
  if (!originAllowed(request)) return json({error: 'Request origin was not allowed.'}, 403);
  if (pathname === '/api/auth/logout' && method === 'POST') {
    return json({signed_out: true}, 200, {'Set-Cookie': 'openkode_admin=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'});
  }
  if (['/api/auth/session', '/api/auth/login', '/api/auth/register', '/api/account/password'].includes(pathname)) {
    return json({error: localBackendMessage}, 503);
  }
  return json({error: 'Page not found.'}, 404);
};

export const config = {
  path: ['/api/auth/session', '/api/auth/login', '/api/auth/register', '/api/auth/logout', '/api/account/password']
};
