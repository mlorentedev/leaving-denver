import cloudflareAccessPlugin from '@cloudflare/pages-plugin-cloudflare-access';

export async function onRequest(context) {
  let path;
  try {
    path = new URL(context.request.url).pathname;
    for (let depth = 0; depth < 3; depth++) {
      const decoded = decodeURIComponent(path);
      if (decoded === path) break;
      path = decoded;
    }
    path = path.replace(/\/+/g, '/');
  } catch {
    return new Response('Invalid request path', { status: 400 });
  }
  if (path !== '/seller' && !path.startsWith('/seller/')) return context.next();

  const domain = context.env.ACCESS_TEAM_DOMAIN;
  const aud = context.env.ACCESS_AUD;
  if (!/^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com$/i.test(domain || '') ||
      !/^[a-f0-9]{64}$/i.test(aud || '')) {
    return new Response('Seller access is not configured', { status: 503 });
  }
  return cloudflareAccessPlugin({ domain, aud })({
    ...context,
    next: (...args) => {
      const payload = context.data.cloudflareAccess?.JWT.payload;
      if (payload?.iss !== domain ||
          !Array.isArray(payload.aud) || !payload.aud.includes(aud) ||
          !Number.isInteger(payload.exp) || payload.exp <= Date.now() / 1000) {
        return new Response('Access token is missing required claims', { status: 403 });
      }
      return context.next(...args);
    },
  });
}
