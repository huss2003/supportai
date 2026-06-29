import os
import sys
import streamlit as st
import requests
from pathlib import Path

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "")
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

PAGES_DIR = Path(__file__).parent / "pages"

st.set_page_config(
    page_title="SupportAI", layout="wide", initial_sidebar_state="expanded"
)


def api_get(path: str, params: dict = None):
    try:
        r = requests.get(
            f"{API_BASE}{path}", headers=HEADERS, params=params, timeout=15
        )
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        st.error(f"Connection refused: {API_BASE}")
        return None
    except requests.HTTPError as e:
        st.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(str(e))
        return None


def api_post(path: str, data: dict = None):
    try:
        r = requests.post(f"{API_BASE}{path}", headers=HEADERS, json=data, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        st.error(f"Connection refused: {API_BASE}")
        return None
    except requests.HTTPError as e:
        st.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(str(e))
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{API_BASE}{path}", headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        st.error(f"Connection refused: {API_BASE}")
        return None
    except requests.HTTPError as e:
        st.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(str(e))
        return None


if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "page" not in st.session_state:
    st.session_state.page = "Overview"


def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
    st.rerun()


# --- login screen ---
if not st.session_state.authenticated:
    st.markdown(
        """
    <style>
    .login-container { max-width: 380px; margin: 12vh auto; text-align: center; }
    .login-container input { width: 100%; padding: 0.6rem; margin: 0.4rem 0; border: 1px solid #e2e8f0; border-radius: 8px; }
    .login-container button { width: 100%; padding: 0.6rem; background: #6366f1; color: #fff; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
    </style>
    <div class="login-container">
      <h1 style="color:#6366f1;">SupportAI</h1>
      <p style="color:#6c757d;">Admin Dashboard</p>
      <form id="login-form">
        <input type="password" placeholder="Access code" id="code" />
        <button type="button" onclick="document.querySelector('#login-form button').innerText='Verifying...'">Sign In</button>
      </form>
    </div>
    """,
        unsafe_allow_html=True,
    )

    code = st.text_input("Access code", type="password", label_visibility="collapsed")
    if st.button("Sign In", use_container_width=True, type="primary"):
        if code == "admin":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid code")
    st.stop()

# --- theme injection ---
theme_js = f"""
<script>
const theme = '{st.session_state.theme}';
document.documentElement.setAttribute('data-theme', theme);
const meta = document.createElement('meta');
meta.name = 'theme-color';
meta.content = theme === 'dark' ? '#0f172a' : '#ffffff';
document.head.appendChild(meta);
</script>
"""
st.markdown(theme_js, unsafe_allow_html=True)

# --- sidebar ---
with st.sidebar:
    st.markdown("## SupportAI")
    st.markdown("---")

    pages = ["Overview", "Tickets", "Conversation", "FAQ Manager"]
    for p in pages:
        if st.button(
            p,
            use_container_width=True,
            type="secondary" if st.session_state.page != p else "primary",
        ):
            st.session_state.page = p
            st.rerun()

    st.markdown("---")
    st.button("Toggle Theme", on_click=toggle_theme, use_container_width=True)

    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- page routing ---
page = st.session_state.page

if page == "Overview":
    from supportai.pages.overview import render

    render(api_get)
elif page == "Tickets":
    from supportai.pages.tickets import render

    render(api_get, api_post)
elif page == "Conversation":
    from supportai.pages.conversation import render

    render(api_get)
elif page == "FAQ Manager":
    from supportai.pages.faq_manager import render

    render(api_get, api_post, api_delete)
