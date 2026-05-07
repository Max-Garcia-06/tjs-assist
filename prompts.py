"""System prompts and optimization instructions for TJ's Assist."""

from __future__ import annotations

# Google shut down the unversioned 1.5 Flash id; use a current Flash-tier model.
# Override with env or Streamlit secret `GEMINI_MODEL` if you prefer another ID.
GEMINI_MODEL = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = (
    "You are a Trader Joe's expert. Use the provided list of CURRENT products "
    "to build the shopping list. If an item isn't in the list, find the closest "
    "branded alternative (call out when you are substituting). "
    "\n\n"
    "Always prefer items that explicitly appear in the inventory text; when you guess "
    "a substitute because something is unavailable, explain that briefly.\n\n"
    "Respond with a SINGLE valid JSON object (no markdown fences) matching this schema:\n"
    "{\n"
    '  \"shopping_list\": [\n'
    "    {\"item\": string, \"in_inventory\": boolean, \"quantity_note\": string, \"tj_match\": string, \"substitute_note\": string}\n"
    "  ],\n"
    '  \"recipe\": {\n'
    '    \"title\": string,\n'
    '    \"servings\": string,\n'
    '    \"timing\": string,\n'
    '    \"ingredients\": [string],\n'
    '    \"steps\": [string]\n'
    "  },\n"
    '  \"new_item_highlights\": [\n'
    "    {\"name\": string, \"category\": string, \"why\": string}\n"
    "  ]\n"
    "}\n\n"
    "Rules for new_item_highlights: Pick 1-2 suggestions ONLY from the "
    "`RECENT_NEW_CANDIDATES` list supplied in the user message (copy names exactly "
    "as given). If that list is empty, return []. Keep each `why` to one concise sentence."
)


MEAL_OPTIMIZATION = {
    "High Protein/Performance": (
        "Emphasize high-protein ingredients (lean meats, Greek yogurt, tofu, lentils, protein-rich "
        "TJ's refrigerated items where available), balanced macros, and practical portions for workouts."
    ),
    "Budget": (
        "Minimize ingredient count and cost; favor pantry staples and lower-price TJ's staples; reuse "
        "ingredients across the recipe wherever possible."
    ),
    "Under 15 Minutes": (
        "The active cooking/assemble time must stay under fifteen minutes using mostly pre-prepped TJ's "
        "items (frozen, fresh prepared, jarred sauces) with very few steps."
    ),
}


def build_user_prompt(
    dish: str,
    meal_mode: str,
    inventory_text: str,
    recent_candidates_text: str,
) -> str:
    mode_tip = MEAL_OPTIMIZATION.get(
        meal_mode,
        "Balance flavor, practicality, and what is likely in stock at Trader Joe's.",
    )

    return (
        f"Dish request: {dish}\n"
        f"Meal optimization mode: {meal_mode}\n"
        f"Mode guidelines: {mode_tip}\n\n"
        "CURRENT_INVENTORY_SUMMARY:\n"
        f"{inventory_text}\n\n"
        "RECENT_NEW_CANDIDATES (choose highlights only from this list):\n"
        f"{recent_candidates_text}\n"
    )
