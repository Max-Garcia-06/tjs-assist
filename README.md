# TJ’s Assist

Streamlit app: shopping lists and recipes anchored to Trader Joe’s catalog snapshots (`products.json`). **Fan project—not affiliated with Trader Joe’s.**

## Deploy with Streamlit Community Cloud (recommended path)

### Prerequisites

1. **GitHub account** and this project pushed to a repository (Community Cloud pulls from GitHub).
2. **Community Cloud account** linked to GitHub: [share.streamlit.io](https://share.streamlit.io/).
3. A **Gemini API key** from Google AI Studio: [Google AI Studio](https://aistudio.google.com/apikey).

### Steps

1. **Push code to GitHub** (from your machine):

   ```bash
   cd /path/to/tjsrecipe
   git init
   git add app.py prompts.py scraper.py tj_theme.py requirements.txt .streamlit .gitignore Dockerfile .dockerignore
   ```

   Decide whether to include **`products.json`**:

   - **Include it** (~2–3k SKUs): first load works without scraping; redeploy after major catalog refreshes if you care.
   - **Omit it**: lighter repo; visitors use **Refresh Inventory** once (hits Trader Joe’s from Streamlit’s servers).

   Recommended also:

   ```bash
   git add README.md products.json    # omit products.json if you prefer
   git commit -m "Initial TJ's Assist publish"
   git branch -M main
   git remote add origin https://github.com/YOU/tjsrecipe.git
   git push -u origin main
   ```

2. **Do not commit secrets.** Never add `GOOGLE_API_KEY`, `.env`, or a real `.streamlit/secrets.toml` to Git.

3. In **streamlit cloud** → **Create app**:

   - **Repository:** your repo and branch (**main**).
   - **Main file path:** `app.py`.

4. **App secrets** → **Secrets** tab (or dashboard “Secrets”). Paste Toml-style values, **Save**:

   ```toml
   GOOGLE_API_KEY = "paste-your-key-here"
   ```

   Optional (only if you use them):

   ```toml
   GEMINI_MODEL = "gemini-2.5-flash"
   ```

5. Wait for the **build**. Open the deployed URL once it turns green.

### After deploy

- **Inventory:** Sidebar → **Refresh Inventory** runs `scraper.py` on Streamlit Cloud. If scraping is blocked by Trader Joe’s for that egress IP, include a **`products.json`** in the repo or run refresh from an environment where it succeeds, then redeploy/update the file.
- **Cost:** Anyone with the app URL triggers **Gemini calls on your Google project** unless you gate access separately.

### Troubleshooting

| Issue | What to try |
|--------|-------------|
| “Add GOOGLE_API_KEY…” | Secrets must be spelled exactly **`GOOGLE_API_KEY`** (or use `GEMINI_API_KEY`; the app accepts both per `resolve_api_key()`). Save secrets and reboot the app from the Cloud UI. |
| Model 404 errors | Put `GEMINI_MODEL = "gemini-2.5-flash"` in Secrets. |
| `products.json missing` | Use **Refresh Inventory** with a numeric store code, or commit/push `products.json`. |

## Local development

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GOOGLE_API_KEY="..."
streamlit run app.py
```

## Docker (optional)

See **`Dockerfile`**. Useful for Railway, Fly.io, Render—not required for Streamlit Community Cloud.
