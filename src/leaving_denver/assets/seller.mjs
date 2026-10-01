const platforms = new Set(['fb', 'cl', 'offerup', 'nextdoor']);

export function makeCopy(item, platform) {
  if (!platforms.has(platform)) throw new RangeError(`Unknown platform: ${platform}`);
  if (typeof item.price !== 'number' || !Number.isFinite(item.price)) {
    throw new TypeError('A public asking price is required');
  }

  const name = item.short_title || item.title;
  const price = `$${item.price.toLocaleString('en-US')}`;
  const title = platform === 'nextdoor'
    ? `DTC moving sale: ${name} (${price})`
    : `${name} - ${price} (DTC)`;
  const introduction = {
    fb: `I am selling my ${item.title} in the Denver Tech Center.`,
    cl: `${item.title}\n\nI am moving and selling my ${name} in DTC.`,
    offerup: `My ${name} is ready for pickup in DTC.`,
    nextdoor: `Hi neighbors,\n\nI am selling my ${item.title} in the Denver Tech Center.`,
  }[platform];
  const details = [
    `Asking price: ${price}.`,
    item.condition && `Condition: ${item.condition}.`,
    item.dimensions && `Dimensions: ${item.dimensions}.`,
    ...(item.specs || []).map(spec => `- ${spec}`),
    item.note && `Details: ${item.note}`,
    item.pickup && `Pickup: ${item.pickup}`,
    'Message me to arrange a time to inspect it. Payment in person at pickup.',
  ].filter(Boolean);
  return {
    title: title.slice(0, platform === 'cl' ? 70 : platform === 'offerup' ? 60 : 100),
    description: `${introduction}\n\n${details.join('\n')}`,
  };
}

if (typeof document !== 'undefined') {
  const items = window.posterItems;
  const select = document.getElementById('item');
  const platform = document.getElementById('platform');
  const title = document.getElementById('title');
  const description = document.getElementById('description');
  const photo = document.getElementById('photo');
  const status = document.getElementById('status');

  for (const [index, item] of items.entries()) {
    const option = document.createElement('option');
    option.value = index;
    option.textContent = `${item.short_title || item.title} · $${item.price.toLocaleString('en-US')}`;
    select.append(option);
  }

  function update() {
    const item = items[Number(select.value)];
    if (!item) return;
    const copy = makeCopy(item, platform.value);
    title.value = copy.title;
    description.value = copy.description;
    photo.hidden = !item.images?.length;
    if (item.images?.length) {
      photo.src = `../${item.images[0]}`;
      photo.alt = item.title;
    }
    status.textContent = '';
  }

  for (const control of [select, platform]) control.addEventListener('change', update);
  for (const button of document.querySelectorAll('[data-copy]')) {
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).value);
        status.textContent = 'Copied to clipboard.';
      } catch {
        status.textContent = 'Copy failed. Select the text and copy it manually.';
      }
    });
  }
  update();
}
