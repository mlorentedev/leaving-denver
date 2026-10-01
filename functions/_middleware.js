import cloudflareAccessPlugin from '@cloudflare/pages-plugin-cloudflare-access';

// /seller/* holds the page that opens the sealed private data (ADR-007): no script but its own,
// no network at all, no framing. Cloudflare's Web Analytics beacon (ADR-005) is therefore
// blocked on this path only. Set on the response itself, not in
// _headers: nothing shows that _headers rules apply to a response that passed through here.
const SELLER_POLICY = [
  "default-src 'none'",
  "script-src 'self'",
  "connect-src 'none'",
  "frame-ancestors 'none'",
  "img-src 'self'",
  "style-src 'self'",
  "font-src 'self'",
  "base-uri 'none'",
  "form-action 'none'",
  "object-src 'none'",
].join('; ');

// A copy, because a response from next() or Response.redirect() may have immutable headers.
function withSellerPolicy(response) {
  const sealed = new Response(response.body, response);
  sealed.headers.set('Content-Security-Policy', SELLER_POLICY);
  return sealed;
}

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
  return withSellerPolicy(await guardSeller(context));
}

async function guardSeller(context) {
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
