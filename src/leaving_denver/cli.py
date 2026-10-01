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
from datetime import date
from pathlib import Path

import yaml

from leaving_denver.config import DIST_DIR, DIST_PRIVATE_DIR, PRIVATE_PANEL_HTML
from leaving_denver.panel import (
    CHANNELS,
    panel_actions,
    panel_rows,
    render_panel,
    takedown_steps,
    write_panel,
)
from leaving_denver.pricing import price_tiers
from leaving_denver.private_data import (
    decrypt_private,
    load_private,
    record_post,
    record_price,
    record_sale,
)
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


def set_status(item_id, status):
    """Set one item's status in the SSOT, save it and rebuild; returns the item."""
    data = load_inventory_yaml()
    target_item = next((item for item in data.get("items", []) if item["id"] == item_id), None)
    if not target_item:
        print(f"Error: Item with ID '{item_id}' not found.")
        sys.exit(1)
    target_item["status"] = status
    save_inventory_yaml(data)
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
    except RuntimeError as err:
        print(f"Error: could not record it privately ({err}). Nothing changed.")
        sys.exit(1)


def cmd_post(args):
    known_item(args.id)
    if args.channel not in CHANNELS:
        print(f"Error: unknown channel '{args.channel}' (one of: {', '.join(CHANNELS)}).")
        sys.exit(1)
    on = day_arg(args.on)
    record_privately(record_post, args.id, args.channel, on)
    print(f"Recorded: {args.id} posted on {args.channel} on {on}.")


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


def cmd_sold(args):
    known_item(args.id)
    today = date.today()
    # The repo is public: the sale goes to the encrypted file first, or nothing changes.
    if args.price is not None:
        record_privately(record_sale, args.id, args.price, today)
    else:
        try:
            record_sale(args.id, None, today)
        except RuntimeError as err:
            print(f"Warning: the sale date was not recorded privately ({err}).")
    target_item = set_status(args.id, "Sold")
    print(
        f"Item '{target_item['title']}' marked as SOLD (Price: ${args.price or target_item.get('recommended_list_price')})."
    )
    print("\n" + "=" * 60)
    print("TAKE THE LISTING DOWN:")
    for step in takedown_steps(args.id, load_private()):
        print(f"- {step}")
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
            w1, w2, w3 = price_tiers(it, reserve.get(it["id"]))
            print(f"{it['id']:<24} ${w1:<14} ${w2:<14} ${w3:<14}")
    print("-" * 80)
    print("Hormozi Protocol: If 0 inquiries within 4-7 days on an item, lower to Week 2 tier.")


def cmd_panel(args):
    """Write the private control panel. Fails closed: no file when the data cannot be read."""
    try:
        if args.private_file:
            private = yaml.safe_load(Path(args.private_file).read_text(encoding="utf-8")) or {}
        else:
            private = decrypt_private()
    except (RuntimeError, OSError) as err:
        print(f"Error: cannot read the private data ({err}). No panel written.")
        sys.exit(1)
    today = date.today()
    rows = panel_rows(load_inventory_yaml(), private, today)
    try:
        out = write_panel(render_panel(rows, today), args.out)
    except RuntimeError as err:
        print(f"Error: {err}")
        sys.exit(1)
    due = panel_actions(rows)
    print(f"Panel written to {out} (private: do not copy it into build/public).")
    print(f"{len(due['renewals'])} Facebook renewals due, {len(due['drops'])} drops open.")


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

    drops_p = subparsers.add_parser("drops", help="Calculate Hormozi 3-week staged pricing drops")
    drops_p.set_defaults(func=cmd_drops)

    panel_p = subparsers.add_parser(
        "panel", help="Write the private control panel (build/private/)"
    )
    panel_p.add_argument(
        "--private-file", help="Read a plain YAML instead of the sops file (e.g. the fixture)"
    )
    panel_p.add_argument("--out", type=Path, default=PRIVATE_PANEL_HTML, help="Where to write it")
    panel_p.set_defaults(func=cmd_panel)

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
