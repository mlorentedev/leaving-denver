const ORIGIN = 'https://leaving-denver.pages.dev';

// One entry per listing form. `title` is the platform's title limit; only Facebook documents a
// description limit. `create` is where the listing is made, for an item and for the car.
export const CHANNELS = {
  fb: {
    lang: 'en', source: 'facebook', title: 100, description: 5000,
    create: ['https://www.facebook.com/marketplace/create/item', 'https://www.facebook.com/marketplace/create/vehicle'],
  },
  'fb-es': {
    lang: 'es', source: 'facebook', title: 100, description: 5000,
    create: ['https://www.facebook.com/marketplace/create/item', 'https://www.facebook.com/marketplace/create/vehicle'],
  },
  cl: {
    lang: 'en', source: 'craigslist', title: 70,
    create: ['https://post.craigslist.org/c/den', 'https://post.craigslist.org/c/den/cto'],
  },
  'cl-es': {
    lang: 'es', source: 'craigslist', title: 70,
    create: ['https://post.craigslist.org/c/den', 'https://post.craigslist.org/c/den/cto'],
  },
  offerup: {
    lang: 'en', source: 'offerup', title: 60,
    create: ['https://offerup.com/post', 'https://offerup.com/post'],
  },
  nextdoor: {
    lang: 'en', source: 'nextdoor', title: 100,
    create: ['https://nextdoor.com/for_sale_and_free/', 'https://nextdoor.com/for_sale_and_free/'],
  },
};

// Payment wording is never written here: it arrives with each item (`payment`), built from the
// inventory and the locales.
const TEXT = {
  en: {
    asking: 'Asking price', mileage: 'Mileage', miles: 'miles', miAbbr: 'mi', title: 'Title',
    condition: 'Condition', dimensions: 'Dimensions', included: 'Included', details: 'Details',
    flaws: 'Known flaws', pickup: 'Pickup', payment: 'Payment', in: 'in',
    noHolds: 'No holds and no deposits: it goes to the first person who confirms a pickup time.',
    bundle: 'Taking several items? Ask me about a bundle price.',
    nextdoorTitle: 'DTC moving sale',
  },
  es: {
    asking: 'Precio', mileage: 'Millaje', miles: 'millas', miAbbr: 'millas', title: 'Título',
    condition: 'Estado', dimensions: 'Dimensiones', included: 'Incluye', details: 'Detalles',
    flaws: 'Defectos conocidos', pickup: 'Recogida', payment: 'Pago', in: 'en',
    noHolds: 'No aparto artículos ni pido depósitos: se lo lleva la primera persona que confirme una hora de recogida.',
    bundle: '¿Varios artículos? Pregúnteme por un precio en paquete.',
    nextdoorTitle: 'Venta por mudanza en DTC',
  },
};

// Opening line by channel. `when` is " in November" (or empty without a month).
const INTROS = {
  fb: ({ item, when }) => `I am moving${when} and selling my ${item.title} in the Denver Tech Center.`,
  cl: ({ item, name, when }) => `${item.title}\n\nI am moving${when} and selling my ${name} in DTC.`,
  offerup: ({ name }) => `My ${name} is ready for pickup in DTC.`,
  nextdoor: ({ item, when }) => `Hi neighbors,\n\nI am moving${when} and selling my ${item.title} in the Denver Tech Center.`,
  'fb-es': ({ item, when }) => `Me mudo${when} y vendo mi ${item.title} en Denver Tech Center.`,
  'cl-es': ({ item, name, when }) => `${item.title}\n\nMe mudo${when} y vendo mi ${name} en DTC.`,
};

// Closing line by channel: how the buyer reaches me, for an item and for the car. No phone
// number is ever offered: platform chat, and Craigslist's own relay.
const CLOSINGS = {
  fb: ['Message me to arrange a time to inspect it.', 'Message me to arrange an inspection and test drive.'],
  cl: ['Reply through Craigslist to arrange a time to inspect it.', 'Reply through Craigslist to arrange an inspection and test drive.'],
  offerup: ['Message me here to arrange pickup.', 'Message me here to arrange an inspection and test drive.'],
  nextdoor: ['Send me a message here if you are interested. Thank you!', 'Send me a message here to arrange an inspection and test drive. Thank you!'],
  'fb-es': ['Escríbame para coordinar una hora para verlo.', 'Escríbame para programar una inspección y prueba de manejo.'],
  'cl-es': ['Responda por Craigslist para coordinar una hora para verlo.', 'Responda por Craigslist para programar una inspección y prueba de manejo.'],
};

const money = amount => `$${amount.toLocaleString('en-US')}`;

// Title, price and description in one paste, for forms that take them together.
export const fullListing = (title, price, description) => `TITLE: ${title}\nPRICE: ${money(price)}\n\n${description}`;
const isCar = item => item.category === 'Vehicle' && Number.isFinite(item.odometer);

function carLines(item, text) {
  return [
    `${text.mileage}: ${item.odometer.toLocaleString('en-US')} ${text.miles}.`,
    item.title_status && `${text.title}: ${item.title_status}.`,
    item.vin && `VIN: ${item.vin}.`,
  ];
}

// Facts that speak for the item; the flaws come after them, in termLines.
function factLines(item, text) {
  const car = isCar(item);
  return [
    `${text.asking}: ${money(item.price)}.`,
    ...(car ? carLines(item, text) : []),
    item.condition && `${text.condition}: ${item.condition}.`,
    !car && item.dimensions && `${text.dimensions}: ${item.dimensions}.`,
    ...(item.specs || []).map(spec => `- ${spec}`),
    item.included?.length && `${text.included}: ${item.included.join(', ')}.`,
    item.note && `${text.details}: ${item.note}`,
  ];
}

function termLines(item, text) {
  return [
    item.flaws?.length && `${text.flaws}: ${item.flaws.join('; ')}.`,
    item.pickup && `${text.pickup}: ${item.pickup}`,
    item.payment && `${text.payment}: ${item.payment}.`,
    text.noHolds,
    !isCar(item) && text.bundle,
  ];
}

function titleFor(platform, item, text) {
  const name = item.short_title || item.title;
  const price = money(item.price);
  if (platform === 'nextdoor') return `${text.nextdoorTitle}: ${name} (${price})`;
  const miles = isCar(item) ? ` - ${item.odometer.toLocaleString('en-US')} ${text.miAbbr}` : '';
  return `${name}${miles} - ${price} (DTC)`;
}

function describe(platform, item, text, month) {
  const name = item.short_title || item.title;
  const when = month ? ` ${text.in} ${month}` : '';
  const intro = INTROS[platform]({ item, name, when });
  const body = [...factLines(item, text), ...termLines(item, text)].filter(Boolean).join('\n');
  return `${intro}\n\n${body}\n\n${CLOSINGS[platform][isCar(item) ? 1 : 0]}`;
}

// The listing for one item on one channel. `config` is the page's settings ({ origin, month }).
// A title over the platform's limit is cut and flagged in `fits`; a description is never cut.
export function makeCopy(item, platform, config = {}) {
  if (!Object.hasOwn(CHANNELS, platform)) throw new RangeError(`Unknown platform: ${platform}`);
  if (typeof item.price !== 'number' || !Number.isFinite(item.price)) {
    throw new TypeError('A public asking price is required');
  }
  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(item.id)) {
    throw new TypeError('A public item slug is required');
  }

  const channel = CHANNELS[platform];
  const own = channel.lang === 'es' ? { ...item, ...item.es } : item;
  const text = TEXT[channel.lang];
  const title = titleFor(platform, own, text);
  const description = describe(platform, own, text, config.month?.[channel.lang]);
  const path = channel.lang === 'es' ? '/es' : '';
  return {
    title: title.slice(0, channel.title),
    description,
    link: `${config.origin || ORIGIN}${path}/i/${item.id}/?utm_source=${channel.source}&utm_campaign=moving-sale`,
    tags: (item.tags || []).join(', '),
    price: String(item.price),
    full: fullListing(title.slice(0, channel.title), item.price, description),
    create: channel.create[isCar(own) ? 1 : 0],
    limits: { title: channel.title, description: channel.description ?? null },
    fits: {
      title: title.length <= channel.title,
      description: !channel.description || description.length <= channel.description,
    },
  };
}

// The sealed envelope (ADR-007). The seal runs in Node (assets/seal.mjs) and the page opens it
// with the same code, so the two cannot drift: AES-256-GCM under a PBKDF2-SHA256 key, with the
// envelope header as the additional data, so an edited header fails the tag.
const VERSION = 1;
const KDF = 'PBKDF2-SHA256';
export const ITERATIONS = 1_000_000;
const SALT_BYTES = 16;
const IV_BYTES = 12;

// Words, in any case, separated by spaces or hyphens: how a phone's keyboard or a password
// manager may hand the phrase back.
export const normalizePassphrase = text => text.toLowerCase().split(/[\s-]+/).filter(Boolean).join(' ');

export function toBase64(bytes) {
  let text = '';
  for (let at = 0; at < bytes.length; at += 8192) text += String.fromCharCode(...bytes.subarray(at, at + 8192));
  return btoa(text);
}

export const fromBase64 = text => Uint8Array.from(atob(text), char => char.charCodeAt(0));

const headerBytes = ({ v, kdf, iter, salt }) => new TextEncoder().encode(JSON.stringify({ v, kdf, iter, salt }));

async function deriveKey(passphrase, salt, iterations) {
  const base = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(normalizePassphrase(passphrase)), 'PBKDF2', false, ['deriveKey'],
  );
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations, hash: 'SHA-256' },
    base, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt'],
  );
}

// A new salt and IV on every seal: the envelope is stored, so the same bytes reach every build.
export async function sealEnvelope(plaintext, passphrase, iterations = ITERATIONS) {
  const salt = crypto.getRandomValues(new Uint8Array(SALT_BYTES));
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const header = { v: VERSION, kdf: KDF, iter: iterations, salt: toBase64(salt) };
  const key = await deriveKey(passphrase, salt, iterations);
  const sealed = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv, additionalData: headerBytes(header), tagLength: 128 },
    key, new TextEncoder().encode(plaintext),
  );
  return { ...header, iv: toBase64(iv), ct: toBase64(new Uint8Array(sealed)) };
}

// The plaintext, or a thrown error when the passphrase or the envelope is wrong. The key is
// derived, used once and dropped: nothing outlives this call.
export async function openEnvelope(envelope, passphrase) {
  const salt = fromBase64(envelope.salt);
  const key = await deriveKey(passphrase, salt, envelope.iter);
  const plain = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: fromBase64(envelope.iv), additionalData: headerBytes(envelope), tagLength: 128 },
    key, fromBase64(envelope.ct),
  );
  return new TextDecoder().decode(plain);
}

// The control panel's rows (FEAT-004), computed here after the private data is open: the sealed
// payload holds the allow-list only, and "overdue" depends on today. `price_tiers` and
// `next_drop` in pricing.py are the same arithmetic (a test compares them); days are ISO
// strings (YYYY-MM-DD), which sort as dates.
const DROP_WINDOWS = ['first_drop', 'second_drop', 'clear_floors'];

// Python rounds a half to the even number; so does this, or the page would differ from
// `make drops` by one step.
function roundHalfEven(value) {
  const down = Math.floor(value);
  const rest = value - down;
  if (rest === 0.5) return down % 2 === 0 ? down : down + 1;
  return rest < 0.5 ? down : down + 1;
}

// [list, drop, floor]: the drop is halfway to the floor, to $5 ($100 for the car). An item with
// no floor on file keeps its list price in all three.
export function priceTiers(item, floor) {
  const list = item.price || 0;
  const low = floor ?? list;
  const step = item.category === 'Vehicle' ? 100 : 5;
  return [list, roundHalfEven((list + low) / 2 / step) * step, low];
}

// The first drop window the price log does not cover yet. A window is covered once a reprice
// is logged on or after the day it opens; the last window is the floor itself. The windows are
// the household schedule: the car has none (OPS-013), so it never gets a next drop.
export function nextDrop(item, floor, drops, today, repricedOn) {
  if (item.status !== 'Available' || item.free || item.category === 'Vehicle') return null;
  const [asking, step, low] = priceTiers(item, floor);
  if (low >= asking) return null;
  const last = repricedOn.reduce((a, b) => (a > b ? a : b), '');
  for (const window of DROP_WINDOWS) {
    const opens = drops[window];
    if (last < opens) {
      return { on: opens, price: window === 'clear_floors' ? low : step, overdue: opens < today };
    }
  }
  return null;
}

const DAY = /^\d{4}-\d{2}-\d{2}/;
const asDay = value => (DAY.test(String(value)) ? String(value).slice(0, 10) : null);
const dayNumber = day => Date.parse(`${day}T00:00:00Z`) / 86_400_000;
const addDays = (day, days) => new Date((dayNumber(day) + days) * 86_400_000).toISOString().slice(0, 10);
const entries = section => Object.entries(section || {});

function postedDays(tracking) {
  const posted = {};
  for (const [channel, days] of entries(tracking.channels)) {
    const sorted = (days || []).map(asDay).filter(Boolean).sort();
    if (sorted.length) posted[channel] = sorted;
  }
  return posted;
}

function readSale(entry) {
  if (entry === undefined || entry === null) return null;
  if (typeof entry === 'object') return { price: entry.price ?? null, at: asDay(entry.at) };
  return { price: entry, at: null };
}

// The soonest renewal across the channels that need one.
function renewDue(posted, renewAfter) {
  const dues = entries(renewAfter).filter(([channel]) => posted[channel])
    .map(([channel, days]) => addDays(posted[channel].at(-1), days));
  return dues.length ? dues.sort()[0] : null;
}

function daysListed(posted, end) {
  const first = Object.values(posted).map(days => days[0]).sort()[0];
  // A sale dated before the first posting (a typo, a backfill) shows 0, never negative days.
  return first === undefined ? null : Math.max(dayNumber(end) - dayNumber(first), 0);
}

function privateRow(item, payload, config, today) {
  const id = item.id;
  const tracking = (payload.tracking || {})[id] || {};
  const posted = postedDays(tracking);
  const log = (tracking.price_log || []).filter(entry => asDay(entry.at))
    .map(entry => ({ at: asDay(entry.at), price: entry.price })).sort((a, b) => (a.at < b.at ? -1 : 1));
  const sale = readSale((payload.sales || {})[id]);
  const floor = (payload.floors || {})[id] ?? null;
  const asking = item.free || item.price === undefined ? null : item.price;
  const due = item.status === 'Sold' ? null : renewDue(posted, config.renew_after_days);
  const soldOn = item.status === 'Sold' && sale ? sale.at : null;
  return {
    id,
    title: item.title,
    category: item.category ?? null,
    status: item.status ?? null,
    free: Boolean(item.free),
    unpublished: item.unpublished === true,
    asking,
    target: (payload.targets || {})[id] ?? null,
    floor,
    daysListed: daysListed(posted, soldOn || today),
    channels: Object.entries(posted).map(([name, days]) => ({ name, last: days.at(-1), posts: days.length })),
    renewDue: due,
    renewOverdue: due !== null && due <= today,
    nextDrop: item.unpublished ? null : nextDrop(item, floor, config.drops, today, log.map(entry => entry.at)),
    priceLog: log,
    logMismatch: log.length > 0 && log.at(-1).price !== asking,
    sale,
    note: (payload.notes || {})[id] ?? null,
  };
}

// One row per roster item, in roster order, then one per id the private data names that the
// roster does not (an unpublished item): its id is inside the ciphertext, so showing it by id
// leaks nothing and hides nothing.
export function buildRows(roster, payload, config, today) {
  const known = new Set(roster.map(item => item.id));
  const unlisted = new Set();
  for (const section of ['floors', 'targets', 'sales', 'tracking', 'notes']) {
    for (const [id] of entries(payload[section])) if (!known.has(id)) unlisted.add(id);
  }
  const extra = [...unlisted].sort().map(id => ({ id, title: id, unpublished: true }));
  return [...roster, ...extra].map(item => privateRow(item, payload, config, today));
}

if (typeof document !== 'undefined') {
  const byId = id => document.getElementById(id);
  const readJson = id => JSON.parse(byId(id).textContent);
  const items = readJson('seller-items');
  const config = readJson('seller-config');
  const select = byId('item');
  const platform = byId('platform');
  const status = byId('status');
  let current = null;
  // The decrypted rows while the page is unlocked; null otherwise. Nothing else holds them.
  let unlocked = null;

  for (const [index, item] of items.entries()) {
    const option = document.createElement('option');
    option.value = index;
    option.textContent = `${item.short_title || item.title} · ${money(item.price)}`;
    select.append(option);
  }

  function showCount(id, length, limit) {
    const count = byId(id);
    count.textContent = limit ? `${length}/${limit}` : '';
    count.classList.toggle('text-red-700', Boolean(limit) && length > limit);
  }

  function showCounts() {
    showCount('title-count', byId('title').value.length, current.limits.title);
    showCount('description-count', byId('description').value.length, current.limits.description);
  }

  function showPhotos(item) {
    const photo = byId('photo');
    const strip = byId('photos');
    photo.hidden = !item.images?.length;
    strip.replaceChildren();
    if (item.images?.length) {
      photo.src = `../${item.images[0]}`;
      photo.alt = item.title;
    }
    for (const image of item.images || []) {
      const entry = byId('photo-template').content.cloneNode(true);
      entry.querySelector('img').src = `../${image}`;
      strip.append(entry);
    }
  }

  function update() {
    const item = items[Number(select.value)];
    if (!item) return;
    current = makeCopy(item, platform.value, config);
    byId('title').value = current.title;
    byId('description').value = current.description;
    byId('tags').value = current.tags;
    byId('link').value = current.link;
    byId('create').href = current.create;
    showCounts();
    showPhotos(item);
    showItemPrivate();
    status.textContent = '';
  }

  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = 'Copied to clipboard.';
    } catch {
      status.textContent = 'Copy failed. Select the text and copy it manually.';
    }
  }

  for (const control of [select, platform]) control.addEventListener('change', update);
  for (const field of ['title', 'description']) byId(field).addEventListener('input', showCounts);
  for (const button of document.querySelectorAll('[data-copy]')) {
    button.addEventListener('click', () => copy(byId(button.dataset.copy).value));
  }
  byId('copy-price').addEventListener('click', () => copy(current.price));
  byId('copy-full').addEventListener('click', () => copy(
    fullListing(byId('title').value, Number(current.price), byId('description').value),
  ));

  // The private views (ADR-007 decision 5). They exist only between a successful unlock and
  // Lock (or pagehide); no storage API is touched, and the key is dropped as soon as it has
  // opened the envelope.
  const NO_MATCH = 'That passphrase does not open the private data.';
  const BLANK = '\u2014';
  const usd = value => (value === null || value === undefined ? BLANK : money(value));
  const dayText = day => {
    if (!day) return BLANK;
    const [year, month, date] = day.split('-').map(Number);
    return new Date(year, month - 1, date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };
  const localDay = () => {
    const now = new Date();
    return [now.getFullYear(), now.getMonth() + 1, now.getDate()].map(String).map(part => part.padStart(2, '0')).join('-');
  };
  const unlockForm = byId('unlock');
  const views = byId('private-views');

  function cell(row, field) {
    return row.querySelector(`[data-field="${field}"]`);
  }

  function rowFlags(row) {
    return [
      row.unpublished && '(not published)',
      row.free && '(free with purchase)',
      row.renewOverdue && 'RENEW DUE',
      row.nextDrop?.overdue && 'DROP OPEN',
    ].filter(Boolean).join(' ');
  }

  function fillRow(article, row) {
    const set = (field, text) => { cell(article, field).textContent = text; };
    set('title', row.title);
    set('flags', rowFlags(row));
    set('status', row.status ?? BLANK);
    set('asking', row.free ? 'free with purchase' : usd(row.asking));
    set('target', usd(row.target));
    set('floor', usd(row.floor));
    set('days', row.daysListed === null ? 'not listed' : String(row.daysListed));
    set('channels', row.channels.map(c => `${c.name} (${dayText(c.last)}${c.posts > 1 ? `, ${c.posts}x` : ''})`).join('; ') || BLANK);
    set('renew', dayText(row.renewDue));
    set('drop', row.nextDrop ? `${usd(row.nextDrop.price)} from ${dayText(row.nextDrop.on)}` : BLANK);
    const log = row.priceLog.map(entry => `${dayText(entry.at)}: ${usd(entry.price)}`).join('; ');
    set('log', (log || BLANK) + (row.logMismatch ? ' (differs from asking)' : ''));
    set('sale', row.sale ? `${usd(row.sale.price)}${row.sale.at ? ` on ${dayText(row.sale.at)}` : ''}` : BLANK);
    set('note', row.note ? `Note: ${row.note}` : '');
    cell(article, 'note').hidden = !row.note;
  }

  function fillDue(rows) {
    const due = byId('due');
    const lines = [
      ...rows.filter(row => row.renewOverdue).map(row => `Renew ${row.id} on Facebook (due ${dayText(row.renewDue)})`),
      ...rows.filter(row => row.nextDrop?.overdue)
        .map(row => `Drop ${row.id} to ${usd(row.nextDrop.price)} (window opened ${dayText(row.nextDrop.on)})`),
    ];
    for (const line of lines.length ? lines : ['Nothing is due.']) {
      const entry = document.createElement('li');
      entry.textContent = line;
      due.append(entry);
    }
  }

  function planCell(text) {
    const entry = document.createElement('td');
    entry.className = 'p-2';
    entry.textContent = text;
    return entry;
  }

  function fillPlan(rows) {
    const total = [0, 0, 0];
    for (const row of rows.filter(r => r.status === 'Available' && !r.free && !r.unpublished)) {
      const tiers = priceTiers({ price: row.asking, category: row.category }, row.floor);
      tiers.forEach((value, at) => { total[at] += value; });
      const line = document.createElement('tr');
      line.className = 'border-t border-neutral-300';
      line.append(planCell(row.title), planCell(usd(tiers[0])),
        planCell(row.floor === null ? BLANK : usd(tiers[1])), planCell(row.floor === null ? BLANK : usd(tiers[2])));
      byId('plan').append(line);
    }
    const sum = document.createElement('tr');
    sum.className = 'border-t border-neutral-300 font-semibold';
    sum.append(planCell('Total'), ...total.map(value => planCell(usd(value))));
    byId('plan-total').append(sum);
    const { first_drop: first, second_drop: second, clear_floors: floors } = config.drops;
    byId('plan-windows').textContent = `The first drop opens ${dayText(first)}, the second ${dayText(second)} and the floors ${dayText(floors)}.`;
  }

  function sealedAt(text) {
    const moment = new Date(text);
    return Number.isNaN(moment.getTime()) ? String(text) : moment.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
  }

  function showViews(payload) {
    const rows = buildRows(config.roster, payload, config, localDay());
    views.replaceChildren(byId('private-template').content.cloneNode(true));
    byId('as-of').textContent = `Private data as of ${sealedAt(payload.sealed_at)}`;
    byId('lock').addEventListener('click', lock);
    fillDue(rows);
    fillPlan(rows);
    for (const row of rows) {
      const article = byId('row-template').content.cloneNode(true);
      fillRow(article, row);
      byId('rows').append(article);
    }
    unlocked = new Map(rows.map(row => [row.id, row]));
  }

  function showItemPrivate() {
    const line = byId('item-private');
    const row = unlocked?.get(items[Number(select.value)]?.id);
    if (!row) {
      line.textContent = '';
      return;
    }
    const parts = [`Floor ${usd(row.floor)}`, `Target ${usd(row.target)}`];
    if (row.nextDrop) parts.push(`Next drop ${usd(row.nextDrop.price)} from ${dayText(row.nextDrop.on)}`);
    line.textContent = parts.join(' \u00b7 ') + (row.note ? `. Note: ${row.note}` : '');
  }

  function lock() {
    unlocked = null;
    views?.replaceChildren();
    byId('item-private').textContent = '';
    if (unlockForm) {
      unlockForm.hidden = false;
      byId('passphrase').value = '';
      byId('unlock-message').textContent = '';
    }
  }

  // The plaintext payload, or null when the passphrase or the envelope is wrong: one answer for
  // both, so a failure tells nothing about which.
  async function open(passphrase) {
    try {
      return JSON.parse(await openEnvelope(readJson('sealed'), passphrase));
    } catch {
      return null;
    }
  }

  async function unlock(event) {
    event.preventDefault();
    const message = byId('unlock-message');
    const button = byId('unlock-button');
    button.disabled = true;
    message.textContent = 'Opening\u2026';
    const payload = await open(byId('passphrase').value);
    button.disabled = false;
    if (!payload) {
      message.textContent = NO_MATCH;
      return;
    }
    try {
      showViews(payload);
      showItemPrivate();
      unlockForm.hidden = true;
      byId('passphrase').value = '';
      message.textContent = '';
    } catch {
      lock();
      message.textContent = 'The private data opened but could not be shown.';
    }
  }

  if (unlockForm) {
    unlockForm.addEventListener('submit', unlock);
    window.addEventListener('pagehide', lock);
  }
  update();
}
