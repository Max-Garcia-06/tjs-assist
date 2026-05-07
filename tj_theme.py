"""Trader Joe's–inspired Streamlit styling (colors only; not affiliated with Trader Joe's)."""

from __future__ import annotations

import streamlit as st

# Warm cream, signature red, ink brown — neighborhood-grocery feel.
TJ_THEME_CSS = """
<style>
@import url("https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,400&display=swap");

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] .main {
  font-family: "DM Sans", "Source Sans Pro", ui-sans-serif, system-ui, sans-serif !important;
  background: radial-gradient(1200px 600px at 10% -10%, rgba(184, 29, 44, 0.06), transparent),
    radial-gradient(900px 500px at 90% 0%, rgba(74, 103, 65, 0.05), transparent),
    linear-gradient(180deg, #fdf6ed 0%, #fffbf5 55%, #f8efe4 100%) !important;
  color: #2a1f1a !important;
}

[data-testid="stHeader"] { background-color: transparent !important; }

[data-testid="stSidebar"] {
  background: linear-gradient(165deg, #fffefb 0%, #fdf4ea 48%, #f8ebe0 100%) !important;
  border-right: 3px solid #b81d2c !important;
  box-shadow: 6px 0 24px rgba(42, 31, 26, 0.06);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label {
  color: #2a1f1a !important;
}

h1 { font-family: "Fraunces", Georgia, serif !important; letter-spacing: -0.02em; }

[data-testid="stMetricValue"] {
  font-family: "DM Sans", sans-serif !important;
  font-weight: 600 !important;
}

/* Buttons */
.stButton > button[kind="primary"] {
  background: linear-gradient(180deg, #c42839 0%, #b81d2c 100%) !important;
  border: 1px solid #8b1520 !important;
  color: #fffdf9 !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  padding: 0.55rem 1.1rem !important;
  box-shadow: 0 2px 0 #7a141c, 0 4px 14px rgba(184, 29, 44, 0.25);
  transition: transform 120ms ease, box-shadow 120ms ease, filter 120ms ease;
}
.stButton > button[kind="primary"]:hover {
  filter: brightness(1.05);
  box-shadow: 0 2px 0 #6d1219, 0 6px 18px rgba(184, 29, 44, 0.32);
  border-color: #b81d2c !important;
}
.stButton > button[kind="secondary"] {
  border-radius: 10px !important;
  border-color: rgba(184, 29, 44, 0.35) !important;
}

/* Inputs */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
  border-radius: 10px !important;
  border: 1px solid rgba(42, 31, 26, 0.12) !important;
  background-color: #fffdf9 !important;
}
[data-testid="stTextInput"] input:focus-within {
  border-color: #b81d2c !important;
  box-shadow: 0 0 0 1px rgba(184, 29, 44, 0.25);
}

/* Radio segmentation */
[data-testid="stRadio"] [role="radiogroup"] label {
  font-weight: 500 !important;
}

/* Alerts */
[data-testid="stAlert"],
div.stAlert {
  border-radius: 12px !important;
  border-left-width: 4px !important;
}

/* Dividers */
hr {
  border: none;
  border-top: 1px dashed rgba(184, 29, 44, 0.25) !important;
  margin: 1rem 0 !important;
}

/* Hero & cards (HTML blocks) */
.tj-hero {
  background: linear-gradient(135deg, #fffdf9 0%, #fff5ec 45%, #fdeee4 100%);
  border: 1px solid rgba(184, 29, 44, 0.15);
  border-radius: 16px;
  padding: 1.5rem 1.75rem 1.35rem;
  margin-bottom: 1.25rem;
  box-shadow: 0 8px 32px rgba(42, 31, 26, 0.07);
  position: relative;
  overflow: hidden;
}
.tj-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    -12deg,
    transparent,
    transparent 14px,
    rgba(184, 29, 44, 0.03) 14px,
    rgba(184, 29, 44, 0.03) 15px
  );
  pointer-events: none;
}
.tj-hero-inner { position: relative; z-index: 1; }
.tj-eyebrow {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #b81d2c;
  margin-bottom: 0.35rem;
}
.tj-hero h1 {
  margin: 0 0 0.35rem 0;
  font-size: clamp(1.75rem, 4vw, 2.35rem);
  color: #1a1210;
  font-family: "Fraunces", Georgia, serif !important;
}
.tj-tagline {
  margin: 0;
  font-size: 1.02rem;
  line-height: 1.5;
  color: #4a3f38;
  max-width: 52ch;
}

.tj-sidebar-brand {
  font-family: "Fraunces", Georgia, serif;
  font-weight: 700;
  font-size: 1.15rem;
  color: #b81d2c;
  margin: -0.25rem 0 0.5rem;
  letter-spacing: 0.02em;
}
.tj-sidebar-sub {
  font-size: 0.82rem;
  color: #5c4f47;
  margin: -0.35rem 0 1rem;
  line-height: 1.4;
}

.tj-card-heading {
  font-family: "Fraunces", Georgia, serif;
  font-weight: 600;
  font-size: 1.15rem;
  color: #8b1520;
  margin: 0 0 0.75rem;
  padding-bottom: 0.4rem;
  border-bottom: 2px solid rgba(184, 29, 44, 0.25);
}

.tj-section-heading {
  font-family: "Fraunces", Georgia, serif;
  font-weight: 600;
  font-size: 1.35rem;
  color: #1a1210;
  margin: 0.75rem 0 0.5rem;
}

.tj-pill {
  display: inline-block;
  margin-top: 0.35rem;
  padding: 0.22rem 0.65rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  background: rgba(74, 103, 65, 0.12);
  color: #354d2f;
  border: 1px solid rgba(74, 103, 65, 0.22);
}

.tj-muted { color: #5c4f47 !important; font-size: 0.9rem; }

.tj-new-card {
  background: linear-gradient(180deg, #f6faf4 0%, #eef5eb 100%);
  border: 1px solid rgba(74, 103, 65, 0.28);
  border-radius: 12px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.65rem;
}
.tj-new-card strong { color: #1a3d24; }
.tj-new-card .tj-cat { color: #355a3a; font-size: 0.88rem; font-weight: 600; margin-top: 0.25rem; }
.tj-new-card .tj-why { color: #3d4a3a; margin-top: 0.5rem; line-height: 1.45; font-size: 0.95rem; }

.tj-recipe-box {
  background: #fffdf9;
  border: 1px solid rgba(42, 31, 26, 0.1);
  border-radius: 12px;
  padding: 1rem 1.15rem;
  margin-top: 0.35rem;
}
.tj-recipe-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.65rem; color: #1a1210; }
.tj-recipe-box ul { margin: 0.25rem 0 0.5rem 1.1rem; padding: 0; }
.tj-recipe-box li { margin: 0.35rem 0; line-height: 1.45; }
.tj-badge-inventory { font-size: 0.78rem; font-weight: 600; color: #355a3a; }
.tj-badge-sub { font-size: 0.78rem; font-weight: 600; color: #8b6914; }

/* Bordered Streamlit containers */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255, 253, 249, 0.65) !important;
  border-color: rgba(184, 29, 44, 0.18) !important;
  border-radius: 14px !important;
  box-shadow: 0 4px 20px rgba(42, 31, 26, 0.05);
}

/* Dataframe / expander */
[data-testid="stExpander"] details {
  border-radius: 12px !important;
  border: 1px solid rgba(42, 31, 26, 0.1) !important;
  background: rgba(255, 253, 249, 0.5) !important;
}
</style>
"""


def inject_trader_joes_theme() -> None:
    st.markdown(TJ_THEME_CSS, unsafe_allow_html=True)
