#!/usr/bin/env python3
"""
Denver Tech Center Moving Sale - Master Management CLI.
Coordinates SSOT (data/inventory.yaml), automated photo synchronization,
public/private builds, 3-week Hormozi drops, and Cloudflare Pages deployment.
"""

import argparse
import http.server
import os
import socketserver
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import BASE_DIR, DIST_DIR
from src.site_builder import build_all, load_inventory_yaml, save_inventory_yaml


def cmd_build(args):
    print("Building Moving Sale platform...")
    build_all()


def cmd_sync(args):
    print("Syncing photos and updating inventory.yaml...")
    from src.image_processor import sync_all_photos

    photo_map = sync_all_photos()
    data = load_inventory_yaml()
    for item in data.get("items", []):
        item_id = item.get("id")
        if item_id in photo_map and photo_map[item_id]:
            item["images"] = photo_map[item_id]
            item["primary_image"] = photo_map[item_id][0]
    save_inventory_yaml(data)
    print("Sync complete. Run 'python3 manage.py build' to recompile sites.")


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
    from src.private_data import floors

    data = load_inventory_yaml()
    items = data.get("items", [])
    reserve = floors()
    if not reserve:
        print("Error: data/private.sops.yaml is not decryptable (sops + age key required).")
        sys.exit(1)

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


def cmd_serve(args):
    port = args.port
    os.chdir(str(BASE_DIR))

    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path):
            # Route / to dist/index.html
            if path == "/" or path.startswith("/catalog/") or path == "/robots.txt":
                return str(DIST_DIR / path.lstrip("/"))
            elif path.startswith("/poster_assistant.html") or path.startswith("/dist_private/"):
                clean = path.replace("/dist_private/", "").lstrip("/")
                return str(BASE_DIR / "dist_private" / clean)
            return super().translate_path(path)

    with socketserver.TCPServer(("", port), CustomHandler) as httpd:
        print("=" * 65)
        print(f"Server active on http://localhost:{port}")
        print(f"Public Minimalist Catalog: http://localhost:{port}/")
        print(f"Private Seller Tool:      http://localhost:{port}/poster_assistant.html")
        print("=" * 65)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


def cmd_deploy_cf(args):
    project_name = args.project_name
    print(f"Deploying dist/ to Cloudflare Pages (Project: {project_name})...")
    cmd = [
        "npx",
        "wrangler",
        "pages",
        "deploy",
        str(DIST_DIR),
        f"--project-name={project_name}",
    ]
    subprocess.run(cmd)


def cmd_test(args):
    print("Running test suite...")
    subprocess.run(["pytest", "tests/"])


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
    serve_p.set_defaults(func=cmd_serve)

    deploy_p = subparsers.add_parser("deploy-cf", help="Deploy public site to Cloudflare Pages")
    deploy_p.add_argument(
        "--project-name", default="leaving-denver", help="Cloudflare Pages project name"
    )
    deploy_p.set_defaults(func=cmd_deploy_cf)

    test_p = subparsers.add_parser("test", help="Run pytest integrity and security suite")
    test_p.set_defaults(func=cmd_test)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
