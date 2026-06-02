import streamlit as st
import json
import base64
import requests
import time
from io import BytesIO
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()

# ── Credentials from .env ─────────────────────────────────────────
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
WP_URL           = os.getenv("WP_URL", "")
WP_USERNAME      = os.getenv("WP_USERNAME", "admin")
WP_APP_PASSWORD  = os.getenv("WP_APP_PASSWORD", "")

# ── Prompts ───────────────────────────────────────────────────────
WRITING_PROMPT = """
You are the Lead SEO Architect for PropertyAcross.com.
Given the raw news seed below, generate ONE comprehensive, evidence-based real estate article.

Rules:
1. Define a micro-topic cluster: [Country/City] + [Asset Niche] + [Intent: yield-seeking | lifestyle | CBI/residency] + [2026]
2. Write a question-based H1 headline targeting core investor benefits.
3. Build the body with question-based H2/H3 subheadings (e.g. "What rental yields can investors expect?").
4. Under each heading: 2–4 short scannable paragraphs, direct answers, backed by hard statistics.
5. Conclude with an FAQ block of 5–7 high-volume Q&As.
6. Minimum 1,000 words. Use HTML formatting for WordPress (h1, h2, h3, p, strong tags only).

Output ONLY a valid JSON object — no markdown fences, no preamble:
{
  "title": "H1 Headline Here",
  "main_content": "Full WordPress HTML content here",
  "image_prompt_16_9": "Cinematic 16:9 real estate image prompt",
  "image_prompt_4_5": "Cinematic 4:5 vertical mobile image prompt"
}
"""

NEWSLETTER_PROMPT = """
You are a senior content strategist for PropertyAcross.com.
Given the article title and content snippet, produce distribution copy for off-site channels.

Output ONLY a valid JSON object — no markdown fences, no preamble:
{
  "substack_text": "Conversational inbox-optimised newsletter (short paras, bold takeaways)",
  "medium_text": "Polished macroeconomic essay with [PULL-QUOTE: ...] tags",
  "linkedin_copy": "Professional B2B tone. List ALL companies/firms/orgs mentioned. Last line MUST be exactly: 👇 Link to full article analysis in the first comment.",
  "x_copy": "Punchy hook-first post under 280 chars with 1-2 hashtags",
  "facebook_copy": "Community investor tone, end with engaging question + hashtags",
  "pinterest_copy": "SEO keyword string for Pinterest description"
}
"""

WP_IMAGE_BASE = (
    "Cinematic 16:9 widescreen real estate editorial thumbnail. "
    "Magazine-style composition, layered cityscape panels, dramatic contrast. "
    "Bold dark gradient bar across lower third. Large bold headline typography, "
    "key words in blue and white. Photorealistic, high-resolution, premium investment media look."
)

INSTAGRAM_IMAGE_BASE = (
    "Cinematic 4:5 vertical real estate editorial thumbnail for Instagram. "
    "Magazine-style mobile-optimised composition, layered skyscraper panels. "
    "Bold dark gradient bar across lower third. Large bold headline typography, "
    "key words in blue and white. Photorealistic, high-resolution, premium investment media look."
)

st.set_page_config(
    page_title="PropertyAcross Content Studio",
    page_icon="🏢",
    layout="wide"
)

# ── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .stTextArea textarea { font-family: 'Courier New', monospace; font-size: 13px; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 16px; font-size: 13px; }
    div[data-testid="stStatusWidget"] { display: none; }
    .stage-done { color: #22c55e; font-weight: 600; }
    .stage-active { color: #3b82f6; font-weight: 600; }
    .title-banner {
        background: #f0f4ff;
        border-left: 4px solid #1a3c6b;
        border-radius: 6px;
        padding: 12px 16px;
        font-size: 14px;
        font-weight: 600;
        color: #1a3c6b;
        margin-bottom: 16px;
    }
    .push-success {
        background: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 8px;
        padding: 12px 16px;
        color: #166534;
        font-size: 13px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────
for key in ["generation_ready", "active_title", "active_content",
            "dist_data", "raw_img_16_9", "raw_img_4_5",
            "image_prompt_16_9", "push_success"]:
    if key not in st.session_state:
        st.session_state[key] = None if key not in ["generation_ready", "push_success"] else False


# ══════════════════════════════════════════════════════════════════
# PIPELINE FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def generate_article(raw_input: str) -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"{WRITING_PROMPT}\n\nRaw news seed:\n{raw_input}"
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    text = response.text.strip()
    s, e = text.find('{'), text.rfind('}')
    if s != -1 and e != -1:
        text = text[s:e+1]
    parsed = json.loads(text)
    return parsed[0] if isinstance(parsed, list) else parsed


def generate_distribution(title: str, content: str) -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = (
        f"{NEWSLETTER_PROMPT}\n\n"
        f"Article title: {title}\n\n"
        f"Content snippet:\n{content[:3000]}"
    )
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=[prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    text = response.text.strip()
    s, e = text.find('{'), text.rfind('}')
    if s != -1 and e != -1:
        text = text[s:e+1]
    return json.loads(text)


def generate_image(prompt_text: str, aspect_ratio: str = "16:9") -> BytesIO | None:
    client = genai.Client(api_key=GEMINI_API_KEY)
    candidates = ["gemini-3.1-flash-image", "gemini-3-pro-image"]
    for model_name in candidates:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio)
                )
            )
            for part in response.parts:
                if part.inline_data:
                    return BytesIO(part.inline_data.data)
        except Exception as img_err:
            st.warning(f"Image model {model_name} failed: {img_err}. Trying next...")
            continue
    return None


def upload_image_to_wp(img_bytes: bytes, filename: str) -> tuple[int | None, str]:
    url = f"{WP_URL}/media"
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "image/jpeg"
    }
    try:
        r = requests.post(url, headers=headers, data=img_bytes, timeout=45)
        if r.status_code == 201:
            data = r.json()
            return data.get("id"), data.get("source_url", "")
        else:
            st.error(f"Media upload failed ({r.status_code}): {r.text[:300]}")
    except Exception as e:
        st.error(f"Media upload error: {e}")
    return None, ""


def push_to_wordpress(title: str, content: str, dist: dict,
                      featured_id: int | None, insta_url: str) -> bool:
    url = f"{WP_URL}/posts"
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "title":          title,
        "content":        content,
        "status":         "draft",
        "featured_media": featured_id or 0,
        "meta": {
            "substack_text":    dist.get("substack_text", ""),
            "medium_text":      dist.get("medium_text", ""),
            "linkedin_copy":    dist.get("linkedin_copy", ""),
            "x_copy":           dist.get("x_copy", ""),
            "facebook_copy":    dist.get("facebook_copy", ""),
            "pinterest_copy":   dist.get("pinterest_copy", ""),
            "instagram_asset":  insta_url,
        }
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        if r.status_code == 201:
            return True
        else:
            st.error(f"WordPress push failed ({r.status_code}): {r.text[:300]}")
    except Exception as e:
        st.error(f"WordPress connection error: {e}")
    return False


# ══════════════════════════════════════════════════════════════════
# UI LAYOUT
# ══════════════════════════════════════════════════════════════════

st.title("🏢 PropertyAcross Content Studio")
st.caption("Transform a raw news seed into a full omnichannel campaign — review everything before it touches WordPress.")
st.markdown("---")

col_left, col_right = st.columns([1, 1.4], gap="large")

# ── LEFT: Input ───────────────────────────────────────────────────
with col_left:
    st.markdown("#### 📡 News seed")
    seed = st.text_area(
        label="Paste raw news facts, sentences, or bullet points:",
        height=180,
        placeholder=(
            "Example: Fractional real estate platform launched in Athens, "
            "allowing global yield-seekers to secure partial stakes in sustainable "
            "timber-hybrid studio apartments starting at €1,000..."
        ),
        label_visibility="collapsed"
    )

    run = st.button("🚀 Run Production Factory Engine",
                    type="primary", use_container_width=True,
                    disabled=not seed.strip())

    st.markdown("---")
    st.markdown("#### ⚙️ Pipeline stages")

    s1 = st.empty()
    s2 = st.empty()
    s3 = st.empty()
    s4 = st.empty()

    def stage(slot, icon, label, state="pending"):
        colour = {"pending": "🔘", "active": "🔵", "done": "✅", "error": "❌"}
        slot.markdown(f"{colour.get(state,'🔘')} **{label}**")

    stage(s1, "1", "SEO deep-dive article")
    stage(s2, "2", "Omnichannel distribution copy")
    stage(s3, "3", "16:9 cinematic cover image")
    stage(s4, "4", "4:5 Instagram vertical asset")

# ── PIPELINE EXECUTION ────────────────────────────────────────────
if run and seed.strip():
    st.session_state.generation_ready = False
    st.session_state.push_success = False

    with col_right:
        with st.status("⚙️ Building asset cluster...", expanded=True) as status:
            try:
                # Stage 1 — Article
                stage(s1, "1", "SEO deep-dive article", "active")
                status.update(label="✍️ Stage 1: Generating 1,000+ word SEO article...")
                article = generate_article(seed)
                st.session_state.active_title   = article.get("title", "Untitled")
                st.session_state.active_content = article.get("main_content", "")
                st.session_state.image_prompt_16_9 = article.get("image_prompt_16_9", "")
                stage(s1, "1", "SEO deep-dive article", "done")

                # Stage 2 — Distribution
                stage(s2, "2", "Omnichannel distribution copy", "active")
                status.update(label="📣 Stage 2: Generating newsletter & social variants...")
                dist = generate_distribution(
                    st.session_state.active_title,
                    st.session_state.active_content
                )
                st.session_state.dist_data = dist
                stage(s2, "2", "Omnichannel distribution copy", "done")

                # Stage 3 — 16:9 image
                stage(s3, "3", "16:9 cinematic cover image", "active")
                status.update(label="🎨 Stage 3: Rendering widescreen cover image...")
                prompt_169 = f"{WP_IMAGE_BASE} Context: {st.session_state.image_prompt_16_9}"
                img_169 = generate_image(prompt_169, "16:9")
                st.session_state.raw_img_16_9 = img_169.getvalue() if img_169 else None
                stage(s3, "3", "16:9 cinematic cover image", "done" if img_169 else "error")

                # Stage 4 — 4:5 image
                stage(s4, "4", "4:5 Instagram vertical asset", "active")
                status.update(label="📱 Stage 4: Rendering vertical Instagram asset...")
                prompt_45 = f"{INSTAGRAM_IMAGE_BASE} Context: {article.get('image_prompt_4_5','')}"
                img_45 = generate_image(prompt_45, "3:4")
                st.session_state.raw_img_4_5 = img_45.getvalue() if img_45 else None
                stage(s4, "4", "4:5 Instagram vertical asset", "done" if img_45 else "error")

                st.session_state.generation_ready = True
                status.update(label="✅ All assets ready — review below.", state="complete", expanded=False)

            except Exception as err:
                status.update(label=f"❌ Pipeline error: {err}", state="error")
                st.error(str(err))

# ── RIGHT: Preview & push ─────────────────────────────────────────
if st.session_state.generation_ready:
    with col_right:

        # Push-success banner
        if st.session_state.push_success:
            st.markdown(
                '<div class="push-success">🏆 Draft successfully pushed to WordPress staging!</div>',
                unsafe_allow_html=True
            )

        # Title banner
        st.markdown(
            f'<div class="title-banner">📌 {st.session_state.active_title}</div>',
            unsafe_allow_html=True
        )

        # 16:9 cover image
        if st.session_state.raw_img_16_9:
            st.image(st.session_state.raw_img_16_9,
                     caption="Generated cinematic cover (16:9)",
                     use_container_width=True)

        # WordPress push button — prominent, gated
        if st.button("🔌 Push Asset Package to WordPress Drafts",
                     type="secondary", use_container_width=True):
            with st.spinner("Uploading images and pushing draft to SiteGround..."):
                featured_id, insta_url = None, ""

                if st.session_state.raw_img_16_9:
                    featured_id, _ = upload_image_to_wp(
                        st.session_state.raw_img_16_9, "featured_cover_169.jpg"
                    )
                if st.session_state.raw_img_4_5:
                    _, insta_url = upload_image_to_wp(
                        st.session_state.raw_img_4_5, "instagram_cover_45.jpg"
                    )

                success = push_to_wordpress(
                    st.session_state.active_title,
                    st.session_state.active_content,
                    st.session_state.dist_data,
                    featured_id,
                    insta_url
                )
                if success:
                    st.session_state.push_success = True
                    st.balloons()
                    st.rerun()

        st.markdown("---")

        # Content tabs
        tab_art, tab_nl, tab_soc, tab_img = st.tabs([
            "📝 Article", "📧 Newsletters", "💼 Socials", "🖼️ Images"
        ])

        with tab_art:
            st.markdown(st.session_state.active_content, unsafe_allow_html=True)

        with tab_nl:
            dist = st.session_state.dist_data or {}
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**📬 Substack / WordPress.com**")
                st.code(dist.get("substack_text", ""), language="text")
            with col_b:
                st.markdown("**📘 Medium**")
                st.code(dist.get("medium_text", ""), language="text")

        with tab_soc:
            dist = st.session_state.dist_data or {}
            st.markdown("**💼 LinkedIn**")
            st.text(dist.get("linkedin_copy", ""))
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🐦 X / Twitter**")
                st.info(dist.get("x_copy", ""))
            with c2:
                st.markdown("**👥 Facebook**")
                st.text(dist.get("facebook_copy", ""))
            st.markdown("---")
            st.markdown("**📌 Pinterest**")
            st.caption(dist.get("pinterest_copy", ""))

        with tab_img:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**16:9 Featured Cover**")
                if st.session_state.raw_img_16_9:
                    st.image(st.session_state.raw_img_16_9, use_container_width=True)
                    st.download_button(
                        "⬇️ Download 16:9",
                        data=st.session_state.raw_img_16_9,
                        file_name="featured_cover.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )
                else:
                    st.warning("Image generation failed or unavailable.")
            with c2:
                st.markdown("**4:5 Instagram / Stories**")
                if st.session_state.raw_img_4_5:
                    st.image(st.session_state.raw_img_4_5, use_container_width=True)
                    st.download_button(
                        "⬇️ Download 4:5",
                        data=st.session_state.raw_img_4_5,
                        file_name="instagram_cover.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )
                else:
                    st.warning("Image generation failed or unavailable.")
