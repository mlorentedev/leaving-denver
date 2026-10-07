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
  curl -fsS --retry "${SMOKE_RETRIES:-10}" --retry-delay "${SMOKE_RETRY_DELAY:-5}" \
    --retry-all-errors "$@"
}

# Pages answers any path it has no file for with index.html and a 200, so a fresh deployment
# can serve the catalog for robots.txt before the real file is up (CI run 36847628465 failed
# "permissive" that way, and the same deployment passed minutes later). Fetch it until it
# reads as robots rules.
robots_txt() {
  local body
  for _ in $(seq 0 "${SMOKE_RETRIES:-10}"); do
    body=$(get "$url/robots.txt") || fail "robots.txt missing"
    grep -q '^User-agent:' <<<"$body" && { printf '%s\n' "$body"; return 0; }
    sleep "${SMOKE_RETRY_DELAY:-5}"
  done
  fail "robots.txt is served as a page, not as robots rules"
}

# The security headers (ADR-010), read where buyers reach the site. The policy is the build's, so
# every inline script of the page as served must be in it: an edge that rewrote the page would
# otherwise leave a deployment whose scripts a browser refuses to run. The wildcard CORS header
# Pages adds is detached by `_headers`, but that is Cloudflare's to honour and nothing offline
# shows it, so a deployment that still sends it is reported and not failed.
# Right after the production alias moves, the edge can answer / with the previous deployment's page
# under the new deployment's headers (CI run 37176954819: the candidate passed, production failed
# on an inline-script hash, and the same URL passed minutes later). So the policy and the page are
# read from one response, and a mismatch is fetched again; one that stays still fails.
security_headers() {
  local stale
  for _ in $(seq 0 "${SMOKE_RETRIES:-10}"); do
    stale=$(policy_mismatch) || exit 1  # policy_mismatch has said why
    [ -z "$stale" ] && return 0
    sleep "${SMOKE_RETRY_DELAY:-5}"
  done
  fail "the Content-Security-Policy does not list an inline script of $url/ ($stale)"
}

# Prints the inline-script hashes of / that its own Content-Security-Policy does not list.
policy_mismatch() {
  local headers value body
  body=$(mktemp)
  headers=$(get -D - -o "$body" "$url/") || { rm -f "$body"; fail "$url/ unreachable"; }
  # curl --retry prints every attempt's headers; the body is the last attempt's, so are these.
  headers=$(awk '/^HTTP\//{block=""} {block=block $0 "\n"} END{printf "%s", block}' <<<"$headers")
  header() { { grep -i "^$1:" <<<"$headers" || true; } | head -1 | cut -d: -f2- | tr -d '\r' | sed 's/^ //'; }
  grep -qi '^x-content-type-options: nosniff' <<<"$headers" || fail "_headers not applied"
  [ "$(header Strict-Transport-Security)" = "max-age=31536000; includeSubDomains" ] \
    || fail "Strict-Transport-Security is not served as max-age=31536000; includeSubDomains"
  [ -n "$(header Permissions-Policy)" ] || fail "Permissions-Policy is not served"
  [ "$(header Cross-Origin-Opener-Policy)" = "same-origin" ] \
    || fail "Cross-Origin-Opener-Policy is not served as same-origin"
  value=$(header Content-Security-Policy)
  [ -n "$value" ] || fail "Content-Security-Policy is not served"
  grep -q "script-src 'self' https://static.cloudflareinsights.com" <<<"$value" \
    || fail "the Content-Security-Policy does not let the Web Analytics beacon in (ADR-005)"
  python3 -c '
import base64, hashlib, re, sys
for attrs, body in re.findall(r"<script\b([^>]*)>(.*?)</script>", sys.stdin.read(), re.S):
    kind = re.search(r"\btype=\"([^\"]*)\"", attrs)
    if "src=" in attrs or (kind and kind.group(1) not in ("module", "text/javascript")):
        continue
    digest = hashlib.sha256(body.replace("\r\n", "\n").encode("utf-8")).digest()
    source = "\x27sha256-" + base64.b64encode(digest).decode() + "\x27"
    if source not in sys.argv[1]:
        print(source)
' "$value" <"$body" || { rm -f "$body"; fail "could not read the inline scripts of $url/"; }
  rm -f "$body"
  [ -z "$(header Access-Control-Allow-Origin)" ] \
    || echo "SMOKE WARN: Access-Control-Allow-Origin is still sent; Pages did not honour the detach" >&2
  return 0
}

# A fresh deployment does not become ready at one instant: while it propagates, edges answer
# the same path 200 or 404 (#232: one 200, then 404 for the next fetch's whole budget). Ready
# is $streak 200s in a row, waited for over a few retry budgets.
streak=${SMOKE_READY_STREAK:-3}
in_a_row=0
for _ in $(seq 1 $(((${SMOKE_RETRIES:-10} + 1) * 2 + streak))); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$url/") || code=000
  if [ "$code" = 200 ]; then in_a_row=$((in_a_row + 1)); else in_a_row=0; fi
  [ "$in_a_row" -ge "$streak" ] && break
  sleep "${SMOKE_RETRY_DELAY:-5}"
done
[ "$in_a_row" -ge "$streak" ] || fail "$url/ did not answer 200 $streak times in a row (last: $code)"

page=$(get "$url/") || fail "$url/ unreachable after it answered 200 $streak times in a row"
# Without a top-level 404.html Pages runs the site as a single-page app and answers any unknown
# path with the catalog and a 200 (BUG-013). A fresh deployment can lag, so retry like `get`.
not_found() {
  local reply code body
  # The body is part of the wait too: CI run 37169206079 got a 404 with another body a second
  # after / was 200, and the same deployment served the not-found page minutes later (#173).
  for _ in $(seq 0 "${SMOKE_RETRIES:-10}"); do
    reply=$(curl -sS -w '\n%{http_code}' "$url/smoke-not-found-$RANDOM/") || reply=$'\nunreachable'
    code=${reply##*$'\n'}
    body=${reply%$'\n'*}
    [ "$code" = 404 ] && grep -Fq 'data-role="not-found"' <<<"$body" && break
    sleep "${SMOKE_RETRY_DELAY:-5}"
  done
  [ "$code" = 404 ] || fail "an unknown path answers $code, not 404"
  grep -Fq 'data-role="not-found"' <<<"$body" || fail "the 404 is not the not-found page"
  grep -qE 'const _C = |data-item=|\b(sms|tel):' <<<"$body" && fail "the 404 page carries contact or item data"
  return 0
}
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
  not_found
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$url/seller/")" = 200 ] && fail "/seller/ answers 200 on the end page"
  get "$url/styles.css" >/dev/null || fail "compiled stylesheet missing"
  # Old share links redirect to the end page of their language; a fresh deployment can lag.
  redirected() {
    local got
    for _ in $(seq 0 "${SMOKE_RETRIES:-10}"); do
      got=$(curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' "$url$1") || got="unreachable"
      [ "$got" = "302 $url$2" ] && return 0
      sleep "${SMOKE_RETRY_DELAY:-5}"
    done
    fail "old share link $1 does not redirect to $2 (got: $got)"
  }
  redirected /i/anything/ /
  redirected /es/i/anything/ /es/
  security_headers
  robots=$(robots_txt) || exit 1  # robots_txt has said why; do not lean on set -e
  grep -A1 -x 'User-agent: \*' <<<"$robots" | grep -qx 'Disallow: /' || fail "robots.txt is permissive"
  for path in /inventory.json /poster_assistant.html /private/inventory.json; do
    grep -qE 'firm_floor_price|pinGateModal' <<<"$(curl -sS "$url$path")" && fail "$path serves private content"
  done
  echo "smoke OK (sale over): $url"
  exit 0
fi
not_found
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

robots=$(robots_txt) || exit 1  # robots_txt has said why; do not lean on set -e
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
# A deploy that replaces the cover can still be served the previous page, naming a photo this
# deployment deleted (#166): fetch the page again until the image it names answers.
for _ in $(seq 0 "${SMOKE_RETRIES:-10}"); do
  cover=$(og image <<<"$page")
  [[ "$cover" == https://* ]] && curl -fsSI "$url/${cover#https://*/}" | grep -qi '^content-type: image/jpeg' && break
  sleep "${SMOKE_RETRY_DELAY:-5}"
  page=$(get "$url/")
done
check_image "$(og image <<<"$page")" "catalog"
share_page() {
  local share
  share=$(get "$url/$1") || fail "/$1 unreachable"
  # A missing share page is a 404 now, but the page's own og:url still proves it is the right one.
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
security_headers

# An unknown path is a 404 (not_found above), so the body is the not-found page, never a private file.
for path in /inventory.json /poster_assistant.html /private/inventory.json; do
  body=$(curl -sS "$url$path")
  grep -qE 'firm_floor_price|pinGateModal' <<<"$body" && fail "$path serves private content"
done

# An anonymous visitor to /seller/ must never get the sealed envelope (Access answers first).
for path in /seller/ /seller/index.html; do
  body=$(curl -sS "$url$path")
  grep -qE 'id="sealed"|"kdf": ?"PBKDF2-SHA256"' <<<"$body" && fail "$path serves the sealed envelope anonymously"
done

echo "smoke OK: $url"
