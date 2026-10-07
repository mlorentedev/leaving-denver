#!/usr/bin/env python3
"""
Denver Tech Center Moving Sale - Master Management CLI.
Coordinates SSOT (data/inventory.yaml), automated photo synchronization,
the public build, staged price drops, the seal of the private data for /seller/ and a
loopback-only preview server. Deploys go through GitHub Actions or `make deploy`.
"""

import argparse
import http.server
import sys
import urllib.parse
from datetime import date
from pathlib import Path

from leaving_denver import seal
from leaving_denver.channels import CHANNELS, VEHICLE_ONLY, takedown_steps
from leaving_denver.config import DIST_DIR
from leaving_denver.pricing import price_tiers
from leaving_denver.private_data import (
    load_private,
    record_post,
    record_price,
    record_sale,
)
from leaving_denver.site_builder import (
    apply_photos,
    build_all,
    check_item_status,
    load_inventory_yaml,
    sale_over,
    sale_schedule,
    save_inventory_yaml,
    set_item_status,
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


def refusing_edit(edit, item_id, status):
    """Run an inventory status edit; a refusal is an error message and exit 1, never a traceback."""
    try:
        edit(item_id, status)
    except ValueError as err:
        print(f"Error: {err} Nothing changed.")
        sys.exit(1)


def set_status(item_id, status):
    """Set one item's status in the SSOT, rebuild; returns the item.

    Only that item's `status:` line is edited, so the owner's comments and layout survive
    (a re-serialization with `save_inventory_yaml` drops every comment: #205)."""
    data = load_inventory_yaml()
    target_item = next((item for item in data.get("items", []) if item["id"] == item_id), None)
    if not target_item:
        print(f"Error: Item with ID '{item_id}' not found.")
        sys.exit(1)
    refusing_edit(set_item_status, item_id, status)
    target_item["status"] = status
    build_all()
    return target_item


def cmd_pending(args):
    item = set_status(args.id, "Pending")
    print(f"Item '{item['title']}' reserved: shown as pending pickup; its bundles are off sale.")


def cmd_available(args):
    item = set_status(args.id, "Available")
    print(f"Item '{item['title']}' is available again.")


def known_item(item_id):
    """The inventory item with this id, or exit with an error."""
    item = next((i for i in load_inventory_yaml().get("items", []) if i["id"] == item_id), None)
    if not item:
        print(f"Error: Item with ID '{item_id}' not found.")
        sys.exit(1)
    return item


def day_arg(text):
    """The --on date (default today), or exit with an error."""
    try:
        return date.fromisoformat(text) if text else date.today()
    except ValueError:
        print(f"Error: '{text}' is not a date (use YYYY-MM-DD).")
        sys.exit(1)


def record_privately(recorder, *record_args):
    """Run one private write; its failure is an error message, never a traceback."""
    try:
        recorder(*record_args)
    except (RuntimeError, ValueError, AttributeError) as err:
        print(f"Error: could not record it privately ({err}). Nothing changed.")
        sys.exit(1)


SALE_OVER_NOTE = "The sale is over: /seller/ is not built."


def offer_seller_update():
    """After a record: ask whether to update /seller/ now. A failure is the command's own.

    With the sale over there is no /seller/ to update (OPS-011): say so, ask nothing."""
    if sale_over(load_inventory_yaml()):
        print(SALE_OVER_NOTE)
        return
    try:
        seal.offer_update()
    except RuntimeError as err:
        print(f"Error: /seller/ was not updated ({err}).")
        sys.exit(1)


def cmd_post(args):
    item = known_item(args.id)
    if args.channel not in CHANNELS:
        print(f"Error: unknown channel '{args.channel}' (one of: {', '.join(CHANNELS)}).")
        sys.exit(1)
    if args.channel in VEHICLE_ONLY and item.get("category") != "Vehicle":
        print(f"Error: '{args.channel}' is only for the vehicle, not '{args.id}'.")
        sys.exit(1)
    on = day_arg(args.on)
    record_privately(record_post, args.id, args.channel, on)
    print(f"Recorded: {args.id} posted on {args.channel} on {on}.")
    offer_seller_update()


def cmd_reprice(args):
    known_item(args.id)
    if args.price <= 0:
        print("Error: the price must be a positive number of dollars.")
        sys.exit(1)
    on = day_arg(args.on)
    record_privately(record_price, args.id, args.price, on)
    print(
        f"Recorded: {args.id} asking ${args.price} from {on}. Edit its price in the inventory too."
    )
    offer_seller_update()


def cmd_sold(args):
    item = known_item(args.id)
    today = date.today()
    # A refused inventory edit must not leave a sale recorded privately (a rerun would record it
    # twice): ask the edit first, record second, write the inventory last (#220).
    refusing_edit(check_item_status, args.id, "Sold")
    # The repo is public: the sale goes to the encrypted file first, or nothing changes.
    if args.price is not None:
        record_privately(record_sale, args.id, args.price, today)
    else:
        try:
            record_sale(args.id, None, today)
        except (RuntimeError, ValueError, AttributeError) as err:
            print(f"Warning: the sale date was not recorded privately ({err}).")
    target_item = set_status(args.id, "Sold")
    print(
        f"Item '{target_item['title']}' marked as SOLD (Price: ${args.price or target_item.get('recommended_list_price')})."
    )
    print("\n" + "=" * 60)
    print("TAKE THE LISTING DOWN:")
    for step in takedown_steps(args.id, load_private(), item.get("category") == "Vehicle"):
        print(f"- {step}")
    print("=" * 60)
    offer_seller_update()


def cmd_seal(args):
    """Seal the private data for /seller/ and set the secret. Needs a terminal."""
    try:
        seal.run_seal()
    except RuntimeError as err:
        print(f"Error: {err}")
        sys.exit(1)


def cmd_drops(args):
    from leaving_denver.private_data import floors

    data = load_inventory_yaml()
    items = data.get("items", [])
    reserve = floors()
    if not reserve:
        print("Error: data/private.sops.yaml is not decryptable (sops + age key required).")
        sys.exit(1)

    schedule = sale_schedule(data["seller"])
    print("SALE TIMELINE")
    for label, key in (
        ("First drop", "first_drop"),
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
            w1, w2, w3 = price_tiers(it, reserve.get(it["id"]))
            print(f"{it['id']:<24} ${w1:<14} ${w2:<14} ${w3:<14}")
    print("-" * 80)
    print("Rule of thumb: if an item draws no inquiries in 4-7 days, lower it to the Week 2 tier.")


def resolve_request_path(path: str) -> Path | None:
    """Map a request path onto a file under build/public/, or None when it escapes it.

    Nothing outside build/public/ is reachable: the repo root holds the encrypted private file
    and, one level up, the age key."""
    path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
    target = (DIST_DIR / path.lstrip("/")).resolve()
    if not target.is_relative_to(DIST_DIR.resolve()):
        return None
    return DIST_DIR / target.relative_to(DIST_DIR.resolve())


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
        print(f"Public catalog: http://{host}:{port}/")
        print(f"Seller tool:    http://{host}:{port}/seller/")
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

    post_p = subparsers.add_parser(
        "post", help="Record a posting or renewal of an item on a channel"
    )
    post_p.add_argument("id", help="Item ID (e.g. sofa-sleeper)")
    post_p.add_argument("channel", choices=sorted(CHANNELS), help="Where it was posted")
    post_p.add_argument("--on", help="Date, YYYY-MM-DD (default: today)")
    post_p.set_defaults(func=cmd_post)

    reprice_p = subparsers.add_parser("reprice", help="Record a change of an item's asking price")
    reprice_p.add_argument("id", help="Item ID (e.g. sofa-sleeper)")
    reprice_p.add_argument("price", type=int, help="New asking price in USD")
    reprice_p.add_argument("--on", help="Date, YYYY-MM-DD (default: today)")
    reprice_p.set_defaults(func=cmd_reprice)

    pending_p = subparsers.add_parser("pending", help="Reserve an item for a pickup and rebuild")
    pending_p.add_argument("id", help="Item ID (e.g. sofa-sleeper)")
    pending_p.set_defaults(func=cmd_pending)

    available_p = subparsers.add_parser(
        "available", help="Put an item back on sale (a pickup fell through) and rebuild"
    )
    available_p.add_argument("id", help="Item ID (e.g. sofa-sleeper)")
    available_p.set_defaults(func=cmd_available)

    drops_p = subparsers.add_parser(
        "drops",
        help="Show the written price windows and each item's staged price tiers (seller only)",
    )
    drops_p.set_defaults(func=cmd_drops)

    seal_p = subparsers.add_parser(
        "seal",
        help="Seal the private data for /seller/ and set SELLER_SEALED (needs a terminal)",
    )
    seal_p.set_defaults(func=cmd_seal)

    serve_p = subparsers.add_parser("serve", help="Serve the built catalog and seller tool locally")
    serve_p.add_argument("--port", type=int, default=8088, help="Port (default: 8088)")
    serve_p.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1). It serves build/public/ with no Access in "
        "front, so a LAN address shows /seller/ (and its sealed data) to that network.",
    )
    serve_p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
