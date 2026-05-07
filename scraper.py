#!/usr/bin/env python3
"""
Harvest Trader Joe's product names and categories for TJ's Assist.

1) BeautifulSoup is used on the public Products landing page to scrape category URLs
   from the Products section navigation.
2) requests POSTs Trader Joe's GraphQL SearchProducts endpoint to pull catalog items
   for a store code, including category breadcrumbs from GraphQL records.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from typing import Any
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "products.json"

GRAPHQL_BODY = """query SearchProducts($pageSize: Int, $currentPage: Int, $storeCode: String, $published: String = "1") {
  products(filter: {store_code: {eq: $storeCode}, published: {eq: $published}}, pageSize: $pageSize, currentPage: $currentPage) {
    items {
      sku
      name
      item_title
      categories { id name url_path }
      new_product
      first_published_date
      availability
      retail_price
      item_characteristics
      __typename
    }
    total_count
    page_info { current_page page_size total_pages __typename }
    __typename
  }
}"""

PRODUCTS_REL_RE = re.compile(r"/home/products(?:/|$)")


def environ_get(key: str, default: str | None = None) -> str | None:
    val = os.environ.get(key)
    return val if val not in (None, "") else default


def environ_list(key: str, default: list[str]) -> list[str]:
    raw = environ_get(key)
    if not raw:
        return list(default)
    return [segment.strip() for segment in raw.split(",") if segment.strip()]


def graphql_urls() -> list[str]:
    override = environ_get("TJ_GRAPHQL_URL")
    if override:
        if "/graphql" in override:
            return [override.rstrip("/")]
        return [urljoin(override.rstrip("/") + "/", "api/graphql")]
    bases = environ_list(
        "TJ_SITE_BASE_URLS",
        [
            "https://www.traderjoes.com",
            "https://publish-p24753-e81973.adobeaemcloud.com",
        ],
    )
    return [urljoin(base.rstrip("/") + "/", "api/graphql") for base in bases]


def browser_headers(site_root: str) -> dict[str, str]:
    origin = f"{urlparse(site_root).scheme}://{urlparse(site_root).netloc}"
    return {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": origin,
        "referer": urljoin(site_root, "/home/products/category"),
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="136", "Google Chrome";v="136"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        ),
    }


def enumerate_products_landing_pages(site_root: str) -> list[str]:
    manual = environ_get("TJ_PRODUCTS_HTML_URLS")
    if manual:
        return [fragment.strip() for fragment in manual.split(",") if fragment.strip()]

    graphql_root = site_root.rstrip("/")
    urls = [
        urljoin(graphql_root + "/", "home/products"),
    ]

    if "traderjoes.com" not in graphql_root.lower():
        urls.insert(0, "https://www.traderjoes.com/home/products")

    if "publish-p24753-e81973" not in graphql_root.lower():
        urls.append("https://publish-p24753-e81973.adobeaemcloud.com/home/products")

    deduped: dict[str, None] = {}
    for landing in urls:
        deduped.setdefault(landing, None)
    return list(deduped.keys())


def derive_label_from_slug(path_fragment: str) -> str:
    slug = urlparse(path_fragment).path.strip("/").rsplit("/", 1)[-1] if "/" in path_fragment else path_fragment
    slug_core = re.sub(r"-(\d+)$", "", slug)
    return slug_core.replace("&", " and ").replace("-", " ").title()


def crawl_strings_for_categories(payload: Any, origin_site: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for nested in node.values():
                walk(nested)
        elif isinstance(node, list):
            for nested in node:
                walk(nested)
        elif isinstance(node, str) and "/home/products/category/" in node:
            if node.startswith("http"):
                resolved = node
            else:
                normalized = node.split(",", 1)[0].strip()
                normalized = normalized if normalized.startswith("/") else f"/{normalized}"
                base = origin_site if origin_site.endswith("/") else f"{origin_site}/"
                resolved = urljoin(base, normalized)
            slug = urlparse(resolved).path
            hits.append((resolved, derive_label_from_slug(slug)))

    walk(payload)
    return hits


def scrape_category_navigation(site_root: str, session: requests.Session) -> list[dict]:
    discovered: dict[str, str] = {}
    landing_pages = enumerate_products_landing_pages(site_root)

    for landing in landing_pages:
        host_root = f"{urlparse(landing).scheme}://{urlparse(landing).netloc}"
        merged_headers_base = browser_headers(host_root)
        merged_headers = {key: val for key, val in merged_headers_base.items() if key != "content-type"}
        merged_headers["accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

        try:
            resp = session.get(
                landing,
                headers={
                    **merged_headers,
                    "referer": host_root + "/",
                },
                timeout=45,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for anchor in soup.select('a[href*="/home/products/category/"]'):
                label = " ".join(anchor.get_text(separator=" ", strip=True).split())
                href = anchor.get("href")
                if not href:
                    continue
                resolved = urljoin(landing, href)
                if not PRODUCTS_REL_RE.search(resolved):
                    continue
                if not label:
                    label = derive_label_from_slug(urlparse(resolved).path)
                discovered[resolved] = label or "Uncategorized Category"
        except requests.RequestException:
            pass

        model_candidates = sorted(
            {
                urljoin(f"{urlparse(landing).scheme}://{urlparse(landing).netloc}", "home/products.model.json"),
                "https://www.traderjoes.com/home/products.model.json",
                "https://publish-p24753-e81973.adobeaemcloud.com/home/products.model.json",
            }
        )

        model_headers = merged_headers.copy()
        model_headers["accept"] = "application/json, text/plain, */*"

        for model_endpoint in model_candidates:
            try:
                parsed_model = urlparse(model_endpoint)
                origin_site = f"{parsed_model.scheme}://{parsed_model.netloc}"
                model_resp = session.get(model_endpoint, headers=model_headers, timeout=45)
                model_resp.raise_for_status()
                model_payload = json.loads(model_resp.text)
                for resolved, label in crawl_strings_for_categories(model_payload, origin_site):
                    if not PRODUCTS_REL_RE.search(resolved):
                        continue
                    discovered.setdefault(resolved, label or derive_label_from_slug(resolved))
            except (requests.RequestException, json.JSONDecodeError, UnicodeDecodeError):
                continue

    return [{"url": url, "name": discovered[url]} for url in sorted(discovered.keys())]


def post_graphql(
    graphql_endpoint: str,
    *,
    session: requests.Session,
    variables: dict,
) -> dict | None:
    site_root = f"{urlparse(graphql_endpoint).scheme}://{urlparse(graphql_endpoint).netloc}"
    resp = session.post(
        graphql_endpoint,
        headers=browser_headers(site_root),
        json={"operationName": "SearchProducts", "variables": variables, "query": GRAPHQL_BODY},
        timeout=60,
    )
    if resp.status_code != 200:
        return None
    parsed = resp.json()
    errors = parsed.get("errors") or []
    if errors:
        return None
    return parsed


def normalize_characteristics(raw: list | None) -> list[str]:
    labels: list[str] = []
    if not isinstance(raw, list):
        return labels

    for entry in raw:
        if isinstance(entry, dict):
            candidate = entry.get("label") or entry.get("code")
            if candidate:
                labels.append(str(candidate))
        elif entry is not None:
            labels.append(str(entry))
    return sorted({label for label in labels if label})


def truthy_flag(value: str | int | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    text = "" if value is None else str(value).strip().lower()
    return text in {"1", "true", "yes"}


def refresh_inventory(
    *,
    output: Path,
    store_code: str,
    page_size: int,
    max_pages: int,
) -> int:
    session = requests.Session()
    graphql_candidates = graphql_urls()

    chosen_endpoint = None
    bootstrap: dict | None = None
    graphql_site_root = ""

    for endpoint in graphql_candidates:
        graphql_site_root = f"{urlparse(endpoint).scheme}://{urlparse(endpoint).netloc}"
        bootstrap = post_graphql(
            endpoint,
            session=session,
            variables={
                "storeCode": store_code,
                "published": "1",
                "currentPage": 1,
                "pageSize": min(max(page_size, 10), 100),
            },
        )
        if bootstrap:
            chosen_endpoint = endpoint
            break

    if not bootstrap or "data" not in bootstrap:
        print("❌ Unable to reach Trader Joe's GraphQL inventory endpoints.", file=sys.stderr)
        print(f"Tried: {graphql_candidates}", file=sys.stderr)
        output.write_text(
            json.dumps(
                {"error": "graphql_unreachable", "tried_urls": graphql_candidates}, indent=2
            ),
            encoding="utf-8",
        )
        return 2

    assert chosen_endpoint is not None

    categories_nav = scrape_category_navigation(graphql_site_root, session)

    products_bucket = bootstrap["data"]["products"]
    page_info = products_bucket.get("page_info") or {}

    aggregated: dict[str, dict] = {}

    items = products_bucket.get("items") or []
    for payload in items:
        sku_raw = payload.get("sku")
        sku = "" if sku_raw is None else str(sku_raw).strip()
        if not sku:
            continue
        category_rows = payload.get("categories") or []
        category_names = [row["name"] for row in category_rows if isinstance(row, dict) and row.get("name")]
        display_name = (
            payload.get("item_title")
            or payload.get("name")
            or sku
        ).strip()

        aggregated[sku] = {
            "sku": sku,
            "display_name": display_name,
            "system_name": (payload.get("name") or "").strip(),
            "categories": category_names,
            "tags": normalize_characteristics(payload.get("item_characteristics")),
            "new_product_flag": truthy_flag(payload.get("new_product")),
            "first_published_date": payload.get("first_published_date"),
            "availability": payload.get("availability"),
            "retail_price": payload.get("retail_price"),
        }

    total_pages = int(page_info.get("total_pages") or 1)
    fetched_page_size = int(page_info.get("page_size") or page_size)
    pages_budget = max(1, min(total_pages, max_pages))

    for page_no in range(2, pages_budget + 1):
        time.sleep(0.2)
        page_payload = post_graphql(
            chosen_endpoint,
            session=session,
            variables={
                "storeCode": store_code,
                "published": "1",
                "currentPage": page_no,
                "pageSize": fetched_page_size,
            },
        )
        if not page_payload:
            break
        next_items = page_payload["data"]["products"].get("items") or []
        if not next_items:
            break

        for payload in next_items:
            sku_raw = payload.get("sku")
            sku = "" if sku_raw is None else str(sku_raw).strip()
            if not sku:
                continue
            category_rows = payload.get("categories") or []
            category_names = [row["name"] for row in category_rows if isinstance(row, dict) and row.get("name")]
            display_name = (
                payload.get("item_title")
                or payload.get("name")
                or sku
            ).strip()

            record = {
                "sku": sku,
                "display_name": display_name,
                "system_name": (payload.get("name") or "").strip(),
                "categories": category_names,
                "tags": normalize_characteristics(payload.get("item_characteristics")),
                "new_product_flag": truthy_flag(payload.get("new_product")),
                "first_published_date": payload.get("first_published_date"),
                "availability": payload.get("availability"),
                "retail_price": payload.get("retail_price"),
            }

            existing = aggregated.get(sku)
            if not existing or len(category_names) > len(existing.get("categories") or []):
                aggregated[sku] = record

    refreshed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    products_sorted = sorted(aggregated.values(), key=lambda row: row["display_name"].lower())

    artifact = {
        "meta": {
            "last_inventory_update": refreshed_at,
            "store_code": store_code,
            "graphql_endpoint": chosen_endpoint,
            "products_home": urljoin(graphql_site_root, "/home/products"),
            "product_count": len(products_sorted),
            "scraped_category_links": len(categories_nav),
        },
        "categories_nav": categories_nav,
        "products": products_sorted,
    }

    output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(
        f"✔ Saved {len(products_sorted)} products to {output} "
        f"(store {store_code}, pages ~{pages_budget}) via {chosen_endpoint}",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh Trader Joe's inventory snapshot.")
    parser.add_argument("--store", default=environ_get("TJ_STORE_CODE", "701"))
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-pages", type=int, default=200)
    args = parser.parse_args()

    try:
        return refresh_inventory(
            output=args.out,
            store_code=str(args.store),
            page_size=int(args.page_size),
            max_pages=int(args.max_pages),
        )
    except requests.RequestException as exc:
        print(f"❌ Network error refreshing inventory: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
