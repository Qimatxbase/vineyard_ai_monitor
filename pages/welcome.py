"""Project introduction, image-led entrance and team story."""
import base64
from pathlib import Path

import streamlit as st

from src.ui.session import enter_workspace
from src.ui.styles import inject_styles


HERO_IMAGE = Path(__file__).resolve().parents[1] / "assets" / "vineyard-welcome.webp"


@st.cache_data(show_spinner=False)
def _image_uri(filename, modified_ns):
    """Cache the local image, invalidating it when the asset changes."""
    return "data:image/webp;base64," + base64.b64encode(Path(filename).read_bytes()).decode("ascii")


def _apply_hero_background():
    if HERO_IMAGE.is_file():
        image = _image_uri(str(HERO_IMAGE), HERO_IMAGE.stat().st_mtime_ns)
        st.markdown(
            f'<style>.st-key-welcome_hero {{background-image: linear-gradient(180deg, rgba(10, 32, 21, .32), rgba(10, 32, 21, .55) 48%, rgba(10, 32, 21, .64)), url("{image}");}}</style>',
            unsafe_allow_html=True,
        )


def _render_header():
    st.markdown(
        '<header class="welcome-topbar"><div class="welcome-wordmark">Vineyard<span>AI MONITOR</span></div>'
        '<nav class="welcome-links" aria-label="Project introduction"><a href="#who-we-are">Who we are</a>'
        '<a href="#what-we-solve">What we solve</a></nav></header>',
        unsafe_allow_html=True,
    )


def _render_hero():
    with st.container(key="welcome_hero", horizontal_alignment="center", vertical_alignment="center", gap="medium"):
        st.markdown(
            '<div class="welcome-hero-copy"><div class="welcome-eyebrow">A clearer view of every row</div>'
            '<h1>See the vineyard.<br>Know where to look.</h1>'
            '<p>Turn aerial imagery into a clearer picture of canopy growth, possible gaps and the places worth a closer look.</p></div>',
            unsafe_allow_html=True,
        )
        with st.container(key="welcome_enter", horizontal=True, horizontal_alignment="center"):
            st.button("Enter our project", on_click=enter_workspace, type="primary", width=246)
        st.markdown(
            '<div class="welcome-hero-note">Explore the vineyard inspection workspace</div>',
            unsafe_allow_html=True,
        )


def _render_story():
    st.markdown(
        '<div class="welcome-scroll-note"><span>DISCOVER THE PROJECT BELOW</span>'
        '<span>Illustrative generated vineyard image</span></div>'
        '<div class="welcome-intro-grid">'
        '<section id="who-we-are" class="welcome-story"><div class="welcome-section-label">THE TEAM</div>'
        '<h2>Who we are</h2><p>We’re a four-person hackathon team bringing product thinking, computer vision, evaluation and data together. '
        'We’re building a practical way to make aerial imagery easier to inspect and act on.</p>'
        '<div class="welcome-disciplines">Product · Computer vision · Evaluation · Data & dashboards</div></section>'
        '<section id="what-we-solve" class="welcome-story"><div class="welcome-section-label">THE CHALLENGE</div>'
        '<h2>What we solve</h2><p>A drone image can cover many vineyard rows. Deciding where to look closer still takes time. '
        'We turn visible canopy differences and possible gaps into an inspection map, so growers can focus their next field check.</p>'
        '<div class="welcome-outcomes"><span>See canopy coverage</span><span>Review unusual regions</span>'
        '<span>Prioritise field checks</span></div></section></div>'
        '<footer class="welcome-bottom-note">Visual screening to support field inspection. Explore RGB analysis, health maps and a simulated drone workflow inside.</footer>',
        unsafe_allow_html=True,
    )


def render():
    inject_styles("welcome.css")
    _apply_hero_background()
    with st.container(key="welcome_page"):
        _render_header()
        _render_hero()
        _render_story()
