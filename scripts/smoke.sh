#!/usr/bin/env bash
# Post-deploy smoke test for a Cloudflare Pages deployment.
# Usage: scripts/smoke.sh https://<deployment>.pages.dev
set -euo pipefail

url="${1:?usage: smoke.sh <deployment-url>}"
url="${url%/}"
fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }
# A fresh deployment can answer / before every path is ready: CI run 36810890186 got a 404
# seconds after / was 200, and the same deployment passed minutes later. Every fetch
# retries, so only a path that stays missing fails.
get() {
  curl -fsS --retry "${SMOKE_RETRIES:-6}" --retry-delay "${SMOKE_RETRY_DELAY:-5}" \
    --retry-all-errors "$@"
}

# A fresh deployment can take a few seconds to answer everywhere.
for _ in 1 2 3 4 5 6; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$url/") && [ "$code" = 200 ] && break
  sleep 5
done
[ "$code" = 200 ] || fail "$url/ returned $code"

page=$(get "$url/")
# The end-of-sale build (OPS-011) has no catalog: tell it by what is served, since smoke runs
# against a URL and not against the repo. It must stay a page with no way to reach the seller.
if grep -Fq 'data-role="sale-over"' <<<"$page"; then
  es_page=$(get "$url/es/")
  grep -Fq 'data-role="sale-over"' <<<"$es_page" || fail "ES is not the end page"
  for served in "$page" "$es_page"; do
    grep -qiE '\b(sms|tel):' <<<"$served" && fail "the end page links to sms: or tel:"
    grep -qE 'const _C = |data-item=' <<<"$served" && fail "the end page carries contact or item data"
  done
  for served in "$page" "$es_page"; do
    grep -qE '[0-9]{3}[^0-9]{0,3}[0-9]{3}[^0-9]{0,3}[0-9]{4}' <<<"$(sed 's/<[^>]*>/ /g' <<<"$served")" \
      && fail "the end page writes out a phone number"
  done
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$url/seller/")" = 200 ] && fail "/seller/ answers 200 on the end page"
  get "$url/styles.css" >/dev/null || fail "compiled stylesheet missing"
  # Old share links redirect to the end page of their language; a fresh deployment can lag.
  redirected() {
    local got
    for _ in $(seq 0 "${SMOKE_RETRIES:-6}"); do
      got=$(curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' "$url$1") || got="unreachable"
      [ "$got" = "302 $url$2" ] && return 0
      sleep "${SMOKE_RETRY_DELAY:-5}"
    done
    fail "old share link $1 does not redirect to $2 (got: $got)"
  }
  redirected /i/anything/ /
  redirected /es/i/anything/ /es/
  get -I "$url/" | grep -qi '^x-content-type-options: nosniff' || fail "_headers not applied"
  grep -A1 -x 'User-agent: \*' <<<"$(get "$url/robots.txt")" | grep -qx 'Disallow: /' || fail "robots.txt is permissive"
  for path in /inventory.json /poster_assistant.html /private/inventory.json; do
    grep -qE 'firm_floor_price|pinGateModal' <<<"$(curl -sS "$url$path")" && fail "$path serves private content"
  done
  echo "smoke OK (sale over): $url"
  exit 0
fi
grep -q 'const _C = {"cc"' <<<"$page" || fail "contact fragments missing from the page"
grep -q '__SELLER_CONTACT__' <<<"$page" && fail "contact placeholder was not replaced"
grep -qE 'floor_price|"floors"' <<<"$page" && fail "the page carries reserve floor data"
grep -Fq 'href="styles.css"' <<<"$page" || fail "EN stylesheet link missing"
grep -q 'cdn.tailwindcss.com' <<<"$page" && fail "EN loads the Tailwind play CDN"
es_page=$(get "$url/es/")
grep -Fq 'href="../styles.css"' <<<"$es_page" || fail "ES stylesheet link missing"
grep -q 'cdn.tailwindcss.com' <<<"$es_page" && fail "ES loads the Tailwind play CDN"
css=$(get "$url/styles.css") || fail "compiled stylesheet missing"
grep -Fq '.aspect-4\/3{' <<<"$css" || fail "Tailwind v4 utility missing"

robots=$(get "$url/robots.txt") || fail "robots.txt missing"
# The catch-all group itself must disallow; a stray "Disallow: /" elsewhere proves nothing.
grep -A1 -x 'User-agent: \*' <<<"$robots" | grep -qx 'Disallow: /' || fail "robots.txt is permissive"
grep -q '^User-agent: facebookexternalhit' <<<"$robots" || fail "robots.txt shuts out link previews"

# Link previews (FEAT-002). og:image is absolute on the production origin; fetch its path
# here, so a preview deployment is checked against its own files.
og() { sed -nE "s/.*<meta property=\"og:$1\" content=\"([^\"]+)\".*/\\1/p" | head -1; }
check_image() {
  [[ "$1" == https://* ]] || fail "$2 has no absolute og:image"
  get -I "$url/${1#https://*/}" | grep -qi '^content-type: image/jpeg' \
    || fail "$2 og:image ${1#https://*/} does not answer as a JPEG"
}
check_image "$(og image <<<"$page")" "catalog"
share_page() {
  local share
  share=$(get "$url/$1") || fail "/$1 unreachable"
  # Unknown paths answer with index.html, so match the page's own og:url, not the status.
  [[ "$(og url <<<"$share")" == */$1 ]] || fail "share page /$1 missing"
  printf '%s' "$share"
}
# Every card has both share pages. An item with no photo has no og:image, which is content,
# not a defect, so the images are checked, in both locales, on the first item that has one.
items=$(grep -oE 'data-item="[^"]+"' <<<"$page" | cut -d'"' -f2)
[ -n "$items" ] || fail "no item cards on the page"
pictured=""
for item in $items; do
  for share_path in "i/$item/" "es/i/$item/"; do
    share=$(share_page "$share_path") || exit 1
    image=$(og image <<<"$share")
    # The pick is made on the English page, so both of the picked item's pages are checked.
    if [ "$pictured" = "$item" ] || { [ -z "$pictured" ] && [ "$share_path" = "i/$item/" ] && [ -n "$image" ]; }; then
      pictured=$item
      check_image "$image" "/$share_path"
    fi
  done
done
[ -n "$pictured" ] || fail "no share page has an og:image"
get -I "$url/" | grep -qi '^x-content-type-options: nosniff' || fail "_headers not applied"

# Pages answers unknown paths with index.html, so check content, not status.
for path in /inventory.json /poster_assistant.html /private/inventory.json; do
  body=$(curl -sS "$url$path")
  grep -qE 'firm_floor_price|pinGateModal' <<<"$body" && fail "$path serves private content"
done

echo "smoke OK: $url"
