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

// Opening line by channel. `when` is " in November" (or empty without a departure month).
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

if (typeof document !== 'undefined') {
  const items = window.posterItems;
  const config = window.sellerConfig;
  const byId = id => document.getElementById(id);
  const select = byId('item');
  const platform = byId('platform');
  const status = byId('status');
  let current = null;

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
  update();
}
