from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import google.generativeai as genai
import pandas as pd
import streamlit as st
from google.api_core.exceptions import NotFound

from prompts import GEMINI_MODEL, MEAL_OPTIMIZATION, SYSTEM_INSTRUCTION, build_user_prompt
from scraper import ROOT
from tj_theme import inject_trader_joes_theme

DATA_PATH = ROOT / "products.json"
DEFAULT_TJ_STORE_CODE = "701"


def normalize_store_code(raw: str) -> str | None:
    candidate = raw.strip()
    if not candidate or not candidate.isdigit():
        return None
    if not 2 <= len(candidate) <= 8:
        return None
    return candidate


def resolve_gemini_model_preference() -> str | None:
    env = os.environ.get("GEMINI_MODEL")
    if env:
        return env.strip()
    try:
        secret = st.secrets.get("GEMINI_MODEL")
        if not secret:
            return None
        return str(secret).strip()
    except FileNotFoundError:
        return None
    except RuntimeError:
        return None


def gemini_model_candidates() -> list[str]:
    preferred = resolve_gemini_model_preference()
    chain = [
        preferred,
        GEMINI_MODEL,
        "gemini-2.5-flash",
        "gemini-3-flash-preview",
        "gemini-flash-latest",
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for name in chain:
        if not name:
            continue
        compact = name.strip()
        if compact and compact not in seen:
            seen.add(compact)
            ordered.append(compact)
    return ordered


def resolve_api_key() -> str | None:
    for candidate in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GENAI_API_KEY"):
        env_value = os.environ.get(candidate)
        if env_value:
            return env_value
    try:
        return (
            st.secrets.get("GOOGLE_API_KEY")
            or st.secrets.get("GEMINI_API_KEY")
            or st.secrets.get("GENAI_API_KEY")
        )
    except FileNotFoundError:
        return None
    except RuntimeError:
        return None


def load_products(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "error" in raw and not raw.get("products"):
        raise ValueError(raw.get("error", "inventory_unavailable"))
    return raw


def initial_store_code_bootstrap() -> str:
    env = os.environ.get("TJ_STORE_CODE")
    if env:
        normalized = normalize_store_code(env)
        if normalized:
            return normalized
    if DATA_PATH.exists():
        try:
            doc = load_products(DATA_PATH)
            from_file = str(doc.get("meta", {}).get("store_code", "")).strip()
            normalized = normalize_store_code(from_file)
            if normalized:
                return normalized
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            pass
    return DEFAULT_TJ_STORE_CODE


def format_inventory_digest(products: list[dict], line_cap: int = 6500) -> str:
    lines: list[str] = []
    for row in sorted(products, key=lambda item: item.get("display_name", "").lower()):
        name = row.get("display_name") or row.get("name") or row.get("system_name")
        cats = ", ".join(row.get("categories") or [])
        novelty = "(new sku)" if row.get("new_product_flag") else ""
        sku = row.get("sku", "")
        line = " | ".join(part for part in (name, sku, cats, novelty) if part).strip()
        if line:
            lines.append(line)
        if len(lines) >= line_cap:
            footer = (
                f"... truncated after {line_cap} SKUs ({len(products)} total downloaded). "
                "Still exhaustive for store-level staples—LLM retains brand expertise for gaps."
            )
            lines.append(footer)
            break
    return "\n".join(lines)


def build_recent_candidate_reference(products: list[dict], limit: int = 42) -> tuple[str, list[str]]:
    frame = pd.DataFrame(products)

    frame["freshness"] = pd.to_datetime(frame["first_published_date"], errors="coerce")
    flagged = frame["new_product_flag"].fillna(False).astype(bool)
    frame_with_flag = frame.assign(_flag=flagged)
    new_items = frame_with_flag[frame_with_flag["_flag"]].sort_values(
        by=["freshness"],
        ascending=False,
        na_position="last",
    )
    rest = frame_with_flag[~frame_with_flag["_flag"]].sort_values(
        by=["freshness"],
        ascending=False,
        na_position="last",
    )
    prioritized = pd.concat([new_items, rest], ignore_index=True)
    prioritized = prioritized.drop_duplicates(subset=["display_name"]).head(limit)

    pretty_lines: list[str] = []
    canonical_names: list[str] = []
    for _, record in prioritized.iterrows():
        name = str(record.get("display_name", "")).strip()
        cats = ", ".join(record.get("categories") or [])
        novelty = (
            "flagged-new"
            if bool(record.get("new_product_flag"))
            else ("recent-publish" if pd.notna(record.get("freshness")) else "")
        )

        snippet = name
        if cats:
            snippet += f" | {cats}"
        if novelty:
            snippet += f" | {novelty}"

        canonical_names.append(name)
        pretty_lines.append(snippet)

    return ("\n".join(pretty_lines), canonical_names)


def extract_json_blob(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    brace_start = cleaned.find("{")
    brace_end = cleaned.rfind("}")
    json_slice = cleaned[brace_start : brace_end + 1]
    return json.loads(json_slice)


def validate_highlights(highlights: list[dict], allowed: list[str]) -> list[dict]:
    allowed_casefold = {name.casefold(): name for name in allowed if name}
    sanitized: list[dict] = []
    for suggestion in highlights:
        name = str(suggestion.get("name", "")).strip()
        canonical = allowed_casefold.get(name.casefold())
        if not canonical:
            continue
        sanitized.append(
            {
                "name": canonical,
                "category": str(suggestion.get("category", "")).strip(),
                "why": str(suggestion.get("why", "")).strip(),
            }
        )
        if len(sanitized) >= 2:
            break
    return sanitized


def run_scraper_subprocess(store_code: str) -> tuple[int, str]:
    script_path = ROOT / "scraper.py"
    completed = subprocess.run(
        [sys.executable, str(script_path), "--store", store_code],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    tail = (completed.stdout + "\n" + completed.stderr).strip()
    return completed.returncode, tail


def render_cached_plan(plan: dict[str, Any], products: list[dict]) -> None:
    """Draw shopping list / recipe / new items without requiring the Generate button rerun."""
    session_key = plan["session_key"]
    payload = plan["payload"]
    highlights = plan["highlights"]
    dish_title = plan["dish"]

    shopping = payload.get("shopping_list") or []
    recipe = payload.get("recipe") or {}

    if plan.get("model_note"):
        st.caption(plan["model_note"])

    st.markdown('<p class="tj-section-heading">New on the shelves</p>', unsafe_allow_html=True)
    if highlights:
        for idea in highlights:
            name = html.escape(str(idea.get("name", "")))
            category = html.escape(str(idea.get("category", "Category TBD")))
            why = html.escape(str(idea.get("why", "")))
            st.markdown(
                f'<div class="tj-new-card"><strong>{name}</strong>'
                f'<div class="tj-cat">{category}</div>'
                f'<div class="tj-why">{why}</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No confident new-item matches from the latest catalog snapshot—try refreshing soon.")

    with st.container(border=True):
        st.markdown('<p class="tj-card-heading">Basket checklist</p>', unsafe_allow_html=True)
        if not shopping:
            st.warning("Gemini did not return shopping list entries.")
        else:
            for idx, row in enumerate(shopping):
                label = str(row.get("item", "Item"))
                detail_bits = []
                if row.get("tj_match"):
                    detail_bits.append(f"TJ match: {row['tj_match']}")
                if row.get("quantity_note"):
                    detail_bits.append(row["quantity_note"])
                if row.get("substitute_note"):
                    detail_bits.append(row["substitute_note"])
                caption = " · ".join(detail_bits)
                column_left, column_right = st.columns((4, 1))
                with column_left:
                    st.checkbox(
                        label,
                        key=f"shop_{session_key}_{idx}",
                        help=caption or None,
                    )
                with column_right:
                    if row.get("in_inventory"):
                        st.markdown(
                            '<span class="tj-badge-inventory">On list</span>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<span class="tj-badge-sub">Verify / sub</span>',
                            unsafe_allow_html=True,
                        )

    st.markdown('<p class="tj-section-heading">Recipe card</p>', unsafe_allow_html=True)
    recipe_title = html.escape(str(recipe.get("title", dish_title)))
    servings = html.escape(str(recipe.get("servings", "n/a")))
    timing = html.escape(str(recipe.get("timing", "")))
    ingredients = recipe.get("ingredients") or []
    steps = recipe.get("steps") or []

    recipe_chunks: list[str] = [
        '<div class="tj-recipe-box">',
        f'<div class="tj-recipe-title">{recipe_title} · '
        f'<span style="font-weight:500;color:#5c4f47">Serves {servings}',
    ]
    if timing:
        recipe_chunks.append(f" · {timing}")
    recipe_chunks.append("</span></div>")

    if ingredients:
        recipe_chunks.append("<p style='margin:0.65rem 0 0.25rem;font-weight:600'>Ingredients</p><ul>")
        for line in ingredients:
            recipe_chunks.append(f"<li>{html.escape(str(line))}</li>")
        recipe_chunks.append("</ul>")
    if steps:
        recipe_chunks.append("<p style='margin:0.65rem 0 0.25rem;font-weight:600'>Steps</p><ol>")
        for line in steps:
            recipe_chunks.append(f"<li>{html.escape(str(line))}</li>")
        recipe_chunks.append("</ol>")
    recipe_chunks.append("</div>")
    st.markdown("".join(recipe_chunks), unsafe_allow_html=True)

    with st.expander("Inventory analytics (pandas)"):
        if not products:
            st.caption("Could not load `products.json` for this view—inventory may be missing or unreadable.")
        else:
            frame = pd.DataFrame(products)
            st.dataframe(
                frame.assign(
                    categories_joined=frame["categories"].apply(lambda cats: " > ".join(cats or [])),
                ),
                use_container_width=True,
                height=320,
            )


st.set_page_config(page_title="TJ's Assist", layout="wide", initial_sidebar_state="expanded")
inject_trader_joes_theme()

if "tj_store_code" not in st.session_state:
    st.session_state.tj_store_code = initial_store_code_bootstrap()

st.markdown(
    """
<div class="tj-hero">
  <div class="tj-hero-inner">
    <span class="tj-eyebrow">Neighborhood list · real SKUs</span>
    <h1>TJ's Assist</h1>
    <p class="tj-tagline">Build a shopping list and recipe from your store’s latest inventory.</p>
    <span class="tj-pill">Unofficial project · not affiliated with Trader Joe’s</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        '<div class="tj-sidebar-brand">Trader Joe\'s · Assist</div>'
        '<p class="tj-sidebar-sub">Your store code & refresh live here. '
        "Find your store code on the Trader Joe's website.</p>",
        unsafe_allow_html=True,
    )
    st.markdown('<p class="tj-card-heading" style="margin-top:0.25rem">Inventory</p>', unsafe_allow_html=True)

    st.text_input(
        "Your store code",
        key="tj_store_code",
        max_chars=8,
        help=(
            "Numeric code for your Trader Joe's (from **Find a Store** on traderjoes.com). "
            "Used when you refresh inventory."
        ),
    )

    if DATA_PATH.exists():
        try:
            snapshot = load_products(DATA_PATH)
            last_update = snapshot["meta"].get("last_inventory_update", "unknown")
            st.metric("Last Inventory Update", last_update)
            file_store = str(snapshot["meta"].get("store_code", "n/a"))
            st.caption(
                f"Snapshot store **{file_store}** · "
                f"{snapshot['meta'].get('product_count', len(snapshot.get('products', [])))} SKUs"
            )
            ui_code = normalize_store_code(str(st.session_state.get("tj_store_code", "")))
            snapshot_store = normalize_store_code(str(file_store))
            if ui_code and snapshot_store and ui_code != snapshot_store:
                st.warning(
                    f"Inventory on disk is for store **{snapshot_store}**, but the field above is **{ui_code}**. "
                    "Refresh to download your store."
                )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            st.warning(f"Could not read products.json ({exc}). Run a refresh to rebuild it.")
    else:
        st.info("No products.json yet—refresh to download the catalog.")

    if st.button("Refresh Inventory", type="primary", use_container_width=True):
        chosen = normalize_store_code(str(st.session_state.get("tj_store_code", "")))
        if not chosen:
            st.error("Enter a numeric store code (often 3 digits, e.g. 701).")
        else:
            with st.spinner(f"Running scraper.py for store {chosen}..."):
                exit_code, logs = run_scraper_subprocess(chosen)
            if logs:
                st.code(logs[-4000:], language="text")
            if exit_code == 0:
                st.success("Inventory refresh complete.")
                st.rerun()
            else:
                st.error("Refresh failed—see logs above.")

    st.divider()
    st.markdown(
        '<p class="tj-muted">Optional env: <code>TJ_GRAPHQL_URL</code>, '
        "<code>TJ_SITE_BASE_URLS</code>, <code>TJ_PRODUCTS_HTML_URLS</code></p>",
        unsafe_allow_html=True,
    )

with st.container(border=True):
    st.markdown('<p class="tj-card-heading">What’s for dinner?</p>', unsafe_allow_html=True)
    col_input, col_mode = st.columns((2, 1))
    with col_input:
        dish = st.text_input(
            "What are you cooking?",
            placeholder="e.g., miso ginger salmon bowls, sheet-pan pollo asado…",
            help="More detail helps match real SKUs from your inventory file.",
        )
    with col_mode:
        meal_mode = st.radio(
            "Meal type",
            options=list(MEAL_OPTIMIZATION.keys()),
            horizontal=True,
            help="High protein, budget-friendly, or under fifteen minutes—pick one.",
        )

    generate = st.button("Build list & recipe", type="primary", use_container_width=True)

if generate:
    if not dish.strip():
        st.warning("Please describe a dish first.")
        st.stop()

    if not DATA_PATH.exists():
        st.error("products.json is missing. Use **Refresh Inventory** in the sidebar.")
        st.stop()

    try:
        inventory_doc = load_products(DATA_PATH)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Unable to read inventory file: {exc}")
        st.stop()

    products = inventory_doc.get("products") or []
    if not products:
        st.error("Inventory file has no products. Run the refresh script.")
        st.stop()

    api_key = resolve_api_key()
    if not api_key:
        st.error("Add `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) to your environment or Streamlit secrets.")
        st.stop()

    digest = format_inventory_digest(products)
    recent_blob, recent_names = build_recent_candidate_reference(products)
    user_prompt = build_user_prompt(dish.strip(), meal_mode, digest, recent_blob)

    genai.configure(api_key=api_key)
    candidates = gemini_model_candidates()
    response = None
    model_used: str | None = None
    last_not_found: NotFound | None = None

    with st.spinner("Asking Gemini Flash to map your dish to real SKUs..."):
        for model_name in candidates:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_INSTRUCTION,
                )
                response = model.generate_content(user_prompt)
                model_used = model_name
                break
            except NotFound as err:
                last_not_found = err
                continue

    if response is None:
        st.error(
            "Could not reach any Gemini Flash model (`gemini-1.5-flash` is retired by Google). "
            f"Tried, in order: {', '.join(candidates)}. "
            f"Set **`GEMINI_MODEL`** to an ID from [Models](https://ai.google.dev/gemini-api/docs/models). "
            f"Last API error: {last_not_found}"
        )
        st.stop()

    model_note = None
    if model_used and candidates and model_used != candidates[0]:
        model_note = f"Using Gemini model `{model_used}` (your first choice was unavailable)."

    if not response.text:
        st.error("Gemini returned an empty response—try again or check API availability.")
        st.stop()

    try:
        payload = extract_json_blob(response.text)
    except json.JSONDecodeError:
        st.error("Unable to parse JSON from Gemini. Raw response shown below for debugging.")
        st.code(response.text)
        st.stop()

    if "plan_session" not in st.session_state:
        st.session_state.plan_session = 0
    st.session_state.plan_session += 1
    session_key = st.session_state.plan_session

    highlights = validate_highlights(payload.get("new_item_highlights") or [], recent_names)
    st.session_state.active_plan = {
        "session_key": session_key,
        "payload": payload,
        "highlights": highlights,
        "dish": dish.strip(),
        "model_note": model_note,
    }

active_plan = st.session_state.get("active_plan")
if active_plan is not None:
    try:
        inventory_doc = load_products(DATA_PATH)
        products_live = inventory_doc.get("products") or []
        render_cached_plan(active_plan, products_live)
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        render_cached_plan(active_plan, [])
elif not generate:
    with st.container(border=True):
        st.markdown(
            '<p class="tj-card-heading">Getting started</p>'
            '<p class="tj-tagline" style="max-width:100%">Enter a dish above, choose a meal mode, '
            "then hit <strong>Build list & recipe</strong>. We’ll anchor everything to your local "
            "<code>products.json</code>.</p>",
            unsafe_allow_html=True,
        )
