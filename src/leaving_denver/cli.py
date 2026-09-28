#!/usr/bin/env python3
"""
Denver Tech Center Moving Sale - Master Management CLI.
Coordinates SSOT (data/inventory.yaml), automated photo synchronization,
public/private builds, staged price drops and a loopback-only preview server.
Deploys go through GitHub Actions or `make deploy`.
"""

import argparse
import http.server
import sys
import urllib.parse
from pathlib import Path

from leaving_denver.config import DIST_DIR, DIST_PRIVATE_DIR
from leaving_denver.site_builder import (
    apply_photos,
    build_all,
    load_inventory_yaml,
    sale_schedule,
    save_inventory_yaml,
)


def cmd_build(args):
    print("Building Moving Sale platform...")
    build_all()


def cmd_sync(args):
    print("Syncing photos and updating inventory.yaml...")
    from leaving_denver.image_processor import sync_all_photos

    photo_map = sync_all_photos()
    data = load_inventory_yaml()
    for item in data.get("items", []):
        item_id = item.get("id")
        if photo_map.get(item_id):
            apply_photos(item, photo_map[item_id])
    save_inventory_yaml(data)
    print("Sync complete. Run 'leaving-denver build' to recompile sites.")


def cmd_sold(args):
    item_id = args.id
    realized_price = args.price
    data = load_inventory_yaml()

    target_item = None
    for item in data.get("items", []):
        if item["id"] == item_id:
            target_item = item
            break

    if not target_item:
        print(f"Error: Item with ID '{item_id}' not found.")
        sys.exit(1)

    target_item["status"] = "Sold"
    if realized_price is not None:
        target_item["realized_price"] = realized_price

    save_inventory_yaml(data)
    print(
        f"Item '{target_item['title']}' marked as SOLD (Price: ${realized_price or target_item.get('recommended_list_price')})."
    )

    # Rebuild
    build_all()

    print("\n" + "=" * 60)
    print("CROSS-POSTING TAKEDOWN CHECKLIST:")
    print("1. Facebook Marketplace: Mark as Sold in 'Your Listings'")
    print("2. Craigslist: Delete post from your account dashboard")
    print("3. OfferUp: Archive / Mark Sold")
    print("4. Nextdoor: Mark as Sold or update post")
    print("=" * 60)


def cmd_drops(args):
    from leaving_denver.private_data import floors

    data = load_inventory_yaml()
    items = data.get("items", [])
    reserve = floors()
    if not reserve:
        print("Error: data/private.sops.yaml is not decryptable (sops + age key required).")
        sys.exit(1)

    schedule = sale_schedule(data["seller"]["departure_date"])
    print("SALE TIMELINE")
    for label, key in (
        ("First drop", "first_drop"),
        ("Second drop", "second_drop"),
        ("Clear floors", "clear_floors"),
        ("Giveaway", "giveaway"),
    ):
        start, end = schedule[key]
        print(f"{label}: {start:%b} {start.day}-{end.day}")
    print()

    print("=" * 80)
    print(f"{'ITEM ID':<24} {'WEEK 1 (LIST)':<15} {'WEEK 2 (DROP)':<15} {'WEEK 3 (FLOOR)':<15}")
    print("-" * 80)
    for it in items:
        if it.get("status") == "Available":
            w1 = it.get("recommended_list_price", 0)
            w3 = reserve.get(it["id"], w1)
            if it.get("category") == "Vehicle":
                w2 = round((w1 + w3) / 2 / 100) * 100
            else:
                w2 = round((w1 + w3) / 2 / 5) * 5
            print(f"{it['id']:<24} ${w1:<14} ${w2:<14} ${w3:<14}")
    print("-" * 80)
    print("Hormozi Protocol: If 0 inquiries within 4-7 days on an item, lower to Week 2 tier.")


def resolve_request_path(path: str) -> Path | None:
    """Map a request path onto a file under build/, or None when it escapes its root.

    /private/ and the poster tool come from build/private/; everything else from
    build/public/, the way Cloudflare Pages serves it. Nothing outside build/ is
    reachable: the repo root holds data/inventory.json (with the reserve floors)
    and, one level up, the age key.
    """
    path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
    if path.startswith("/private/") or path.startswith("/poster_assistant.html"):
        root, rel = DIST_PRIVATE_DIR, path.removeprefix("/private/")
    else:
        root, rel = DIST_DIR, path
    target = (root / rel.lstrip("/")).resolve()
    if not target.is_relative_to(root.resolve()):
        return None
    return root / target.relative_to(root.resolve())


class PreviewHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        resolved = resolve_request_path(path)
        return str(resolved) if resolved else ""

    def send_head(self):
        if resolve_request_path(self.path) is None:
            self.send_error(404)
            return None
        return super().send_head()


def make_server(port: int, host: str = "127.0.0.1") -> http.server.ThreadingHTTPServer:
    return http.server.ThreadingHTTPServer((host, port), PreviewHandler)


def cmd_serve(args):
    with make_server(args.port, args.host) as httpd:
        host, port = httpd.server_address[:2]
        print("=" * 65)
        print(f"Public catalog:      http://{host}:{port}/")
        print(f"Private seller tool: http://{host}:{port}/poster_assistant.html")
        print("=" * 65)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


def main():
    parser = argparse.ArgumentParser(description="Moving Sale Master CLI")
    subparsers = parser.add_subparsers(dest="command")

    build_p = subparsers.add_parser("build", help="Sync photos, compile SSOT, and build sites")
    build_p.set_defaults(func=cmd_build)

    sync_p = subparsers.add_parser("sync", help="Auto-discover photos and update inventory.yaml")
    sync_p.set_defaults(func=cmd_sync)

    sold_p = subparsers.add_parser("sold", help="Mark item as sold and trigger rebuild")
    sold_p.add_argument("id", help="Item ID (e.g. sofa-sleeper)")
    sold_p.add_argument("price", nargs="?", type=int, help="Realized sale price in USD")
    sold_p.set_defaults(func=cmd_sold)

    drops_p = subparsers.add_parser("drops", help="Calculate Hormozi 3-week staged pricing drops")
    drops_p.set_defaults(func=cmd_drops)

    serve_p = subparsers.add_parser("serve", help="Serve catalog and seller tool locally")
    serve_p.add_argument("--port", type=int, default=8088, help="Port (default: 8088)")
    serve_p.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1). The private tool is served too, so "
        "binding a LAN address exposes the reserve floors to that network.",
    )
    serve_p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
