#!/usr/bin/env bash
# Post-deploy smoke test for a Cloudflare Pages deployment.
# Usage: scripts/smoke.sh https://<deployment>.pages.dev
set -euo pipefail

url="${1:?usage: smoke.sh <deployment-url>}"
url="${url%/}"
fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }

# A fresh deployment can take a few seconds to answer everywhere.
for _ in 1 2 3 4 5 6; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$url/") && [ "$code" = 200 ] && break
  sleep 5
done
[ "$code" = 200 ] || fail "$url/ returned $code"

page=$(curl -fsS "$url/")
grep -q 'const _C = {"cc"' <<<"$page" || fail "contact fragments missing from the page"
grep -q '__SELLER_CONTACT__' <<<"$page" && fail "contact placeholder was not replaced"
grep -qE 'floor_price|"floors"' <<<"$page" && fail "the page carries reserve floor data"
grep -Fq 'href="styles.css"' <<<"$page" || fail "EN stylesheet link missing"
grep -q 'cdn.tailwindcss.com' <<<"$page" && fail "EN loads the Tailwind play CDN"
es_page=$(curl -fsS "$url/es/")
grep -Fq 'href="../styles.css"' <<<"$es_page" || fail "ES stylesheet link missing"
grep -q 'cdn.tailwindcss.com' <<<"$es_page" && fail "ES loads the Tailwind play CDN"
css=$(curl -fsS "$url/styles.css") || fail "compiled stylesheet missing"
grep -Fq '.aspect-4\/3{' <<<"$css" || fail "Tailwind v4 utility missing"

robots=$(curl -fsS "$url/robots.txt") || fail "robots.txt missing"
grep -q 'Disallow: /' <<<"$robots" || fail "robots.txt is permissive"
grep -q '^User-agent: facebookexternalhit' <<<"$robots" || fail "robots.txt shuts out link previews"

# Link previews (FEAT-002). og:image is absolute on the production origin; fetch its path
# here, so a preview deployment is checked against its own files.
og() { sed -nE "s/.*<meta property=\"og:$1\" content=\"([^\"]+)\".*/\\1/p" | head -1; }
check_image() {
  [[ "$1" == https://* ]] || fail "$2 has no absolute og:image"
  curl -fsSI "$url/${1#https://*/}" | grep -qi '^content-type: image/jpeg' \
    || fail "$2 og:image ${1#https://*/} does not answer as a JPEG"
}
check_image "$(og image <<<"$page")" "catalog"
item=$(grep -oE 'data-item="[^"]+"' <<<"$page" | head -1 | cut -d'"' -f2)
[ -n "$item" ] || fail "no item cards on the page"
for share_path in "i/$item/" "es/i/$item/"; do
  share=$(curl -fsS "$url/$share_path") || fail "/$share_path unreachable"
  # Unknown paths answer with index.html, so match the page's own og:url, not the status.
  [[ "$(og url <<<"$share")" == */$share_path ]] || fail "share page /$share_path missing"
  check_image "$(og image <<<"$share")" "/$share_path"
done
curl -fsSI "$url/" | grep -qi '^x-content-type-options: nosniff' || fail "_headers not applied"

# Pages answers unknown paths with index.html, so check content, not status.
for path in /inventory.json /poster_assistant.html /private/inventory.json; do
  body=$(curl -sS "$url$path")
  grep -qE 'firm_floor_price|pinGateModal' <<<"$body" && fail "$path serves private content"
done

echo "smoke OK: $url"
