// First-party event beacon (FEAT-015, ADR-011): the catalog page posts what a buyer did (arrived
// from a channel, opened an item, tapped "text me") and this writes one data point to Workers
// Analytics Engine. Nothing personal is read or kept: no header, no IP, no `request.cf`, no cookie,
// and the page never sends the phone number (ADR-002). Only the body of the request is read.
//
// The point is [event, source, item, bundle, locale] with a count of one, so the digest groups by
// blob. A beacon must never become an error page: bad input is a 400 and nothing else is ever
// a failure, so a missing or failing dataset still answers 204.

const EVENTS = new Set(['visit', 'view_item', 'text_tap']);
// The channels the seller tool and `make post` emit, the printed flyer and the social page's
// links. A channel that is missing here reads as `other` in the digest;
// tests/test_hit_function.py fails when one is.
const SOURCES = new Set([
  'flyer', 'facebook', 'craigslist', 'offerup', 'nextdoor', 'activebuilding', 'carscom', 'direct',
  'instagram', 'whatsapp',
]);
const LOCALES = new Set(['en', 'es']);
const SLUG = /^[a-z0-9-]{1,64}$/;
const MAX_BODY = 1024;

const slug = (value) => (typeof value === 'string' && SLUG.test(value) ? value : '');

function source(value) {
  if (typeof value !== 'string' || value === '') return 'direct';
  return SOURCES.has(value) ? value : 'other';
}

function parse(text) {
  if (text.length > MAX_BODY) return null;
  try {
    const body = JSON.parse(text);
    const plain = body !== null && typeof body === 'object' && !Array.isArray(body);
    return plain && typeof body.event === 'string' && EVENTS.has(body.event) ? body : null;
  } catch {
    return null;
  }
}

export async function onRequestPost({ request, env }) {
  const body = parse(await request.text());
  if (!body) return new Response('Bad event', { status: 400 });
  try {
    env.SALE_METRICS?.writeDataPoint({
      blobs: [
        body.event,
        source(body.source),
        slug(body.item),
        slug(body.bundle),
        LOCALES.has(body.locale) ? body.locale : 'en',
      ],
      doubles: [1],
      indexes: [body.event],
    });
  } catch {
    // The dataset is a convenience: losing one count is not the buyer's problem.
  }
  return new Response(null, { status: 204 });
}

// Pages tries the method's own handler first; this catches every other method.
export function onRequest() {
  return new Response('POST only', { status: 405, headers: { Allow: 'POST' } });
}
