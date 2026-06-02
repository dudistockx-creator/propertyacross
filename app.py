import streamlit as st
import json
import base64
import requests
from dotenv import load_dotenv
import os

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
WP_URL             = os.getenv("WP_URL", "")
WP_USERNAME        = os.getenv("WP_USERNAME", "admin")
WP_APP_PASSWORD    = os.getenv("WP_APP_PASSWORD", "")

# ── Prompts ───────────────────────────────────────────────────────

WRITING_PROMPT = """
You are the Lead SEO Architect for PropertyAcross.com — a premium global real estate investment publication.

Using the raw news seed below AND your live web search capabilities, generate ONE comprehensive, evidence-based real estate article enriched with current market data, recent statistics, and cited sources.

STRICT RULES:
1. Search the web for the latest data, yield figures, price points, and market statistics related to the topic.
2. Define a micro-topic cluster: [Country/City] + [Asset Niche] + [Intent: yield-seeking | lifestyle | CBI/residency] + [2026]
3. Write a bold, specific, question-based H1 headline that directly addresses investor benefit.
4. Build the body with question-based H2/H3 subheadings pulling from real investor concerns.
5. Under each heading: 2–4 short scannable paragraphs, direct answers, backed by hard statistics, yield figures, price points, and historical comparisons sourced from your web search.
6. Every key claim MUST be backed by a concrete number, percentage, or data point with a source reference.
7. Conclude with a rich FAQ block of 5–7 high-volume Q&As mirroring common search queries.
8. Minimum 1,200 words. Use clean HTML for WordPress (h1, h2, h3, p, strong, ul, li tags only).
9. Tone: authoritative, direct, no fluff, written for serious investors not casual readers.

Output ONLY a valid JSON object — no markdown fences, no preamble:
{
  "title": "H1 Headline Here",
  "main_content": "Full WordPress HTML content here"
}
"""

NEWSLETTER_PROMPT = """
You are a world-class financial newsletter writer for PropertyAcross.com.
Your writing style sits between The Economist's precision and Morning Brew's readability.
Investors actually look forward to reading your emails.

Given the article title and full content below, produce distribution copy for all channels.

SUBSTACK / WORDPRESS.COM VARIANT:
- Open with a punchy 1-sentence hook that makes the reader stop scrolling
- Write like you're sending a personal note to a smart friend who invests in property
- Short paragraphs (2-3 sentences max), bold key data points
- Include a "Why this matters right now" section
- End with a specific thought-provoking question to drive replies
- Aim for 350-450 words
- Tone: insider, warm, direct, genuinely interesting

MEDIUM VARIANT:
- Write a polished long-form financial essay (500-600 words)
- Open with a compelling scene or bold statement that reframes how the reader thinks about this market
- Use [PULL-QUOTE: "..."] tags around your 2-3 strongest data-backed insights
- Structure: hook → market context → deep analysis → forward outlook → call to action
- Tone: sophisticated, analytical, written for tech-savvy business readers
- Make it genuinely worth reading — not just a rewrite of the article

LINKEDIN VARIANT:
- Open with a single bold line that stops the scroll (no "Excited to share..." ever)
- Write in tight punchy staccato lines with line breaks between each thought
- Lead with the most surprising or counterintuitive data point from the article
- Include a mini data breakdown using → arrows or numbered points
- Reference specific companies, developers, government bodies, and architects involved
- Build genuine tension or intrigue — make people want to read the full piece
- End with one sharp insight or question, then on a new line: "👇 Link to full article analysis in the first comment."
- Aim for 200-250 words maximum
- NO generic buzzwords. NO "game-changer". NO "exciting opportunity".

X / TWITTER: Punchy hook-first post under 280 chars with 1-2 hashtags.
FACEBOOK: Community investor tone, ends with engaging question + hashtags.
PINTEREST: SEO keyword string.

Output ONLY a valid JSON object — no markdown fences, no preamble:
{
  "substack_text": "...",
  "medium_text": "...",
  "linkedin_copy": "...",
  "x_copy": "...",
  "facebook_copy": "...",
  "pinterest_copy": "..."
}
"""

# ── Streamlit config ──────────────────────────────────────────────

st.set_page_config(
    page_title="PropertyAcross Content Studio",
    page_icon="🏢",
    layout="wide"
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .stTextArea textarea { font-family: 'Courier New', monospace; font-size: 13px; }
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

for key in ["generation_ready", "push_success", "active_title",
            "active_content", "dist_data"]:
    if key not in st.session_state:
        st.session_state[key] = False if key in ["generation_ready", "push_success"] else None


# ── Pipeline functions ────────────────────────────────────────────

def call_perplexity(messages: list, model: str = "sonar-pro") -> str:
    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000,
        },
        timeout=120
    )
    if response.status_code != 200:
        raise Exception(f"Perplexity API error ({response.status_code}): {response.text[:300]}")
    return response.json()["choices"][0]["message"]["content"]


def generate_article(raw_input: str) -> dict:
    messages = [
        {"role": "system", "content": WRITING_PROMPT},
        {"role": "user",   "content": f"Raw news seed:\n{raw_input}"}
    ]
    text = call_perplexity(messages, model="sonar-pro")
    text = text.strip()
    s, e = text.find('{'), text.rfind('}')
    if s != -1 and e != -1:
        text = text[s:e+1]
    parsed = json.loads(text)
    return parsed[0] if isinstance(parsed, list) else parsed


def generate_distribution(title: str, content: str) -> dict:
    messages = [
        {"role": "system", "content": NEWSLETTER_PROMPT},
        {"role": "user",   "content": f"Article title: {title}\n\nFull article content:\n{content}"}
    ]
    text = call_perplexity(messages, model="sonar")
    text = text.strip()
    s, e = text.find('{'), text.rfind('}')
    if s != -1 and e != -1:
        text = text[s:e+1]
    return json.loads(text)


def push_to_wordpress(title: str, content: str, dist: dict) -> bool:
    url = f"{WP_URL}/posts"
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "title":   title,
        "content": content,
        "status":  "draft",
        "meta": {
            "substack_text":  dist.get("substack_text", ""),
            "medium_text":    dist.get("medium_text", ""),
            "linkedin_copy":  dist.get("linkedin_copy", ""),
            "x_copy":         dist.get("x_copy", ""),
            "facebook_copy":  dist.get("facebook_copy", ""),
            "pinterest_copy": dist.get("pinterest_copy", ""),
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


# ── UI ────────────────────────────────────────────────────────────

st.title("🏢 PropertyAcross Content Studio")
st.caption("Perplexity-powered research · WordPress push")
st.markdown("---")

col_left, col_right = st.columns([1, 1.4], gap="large")

with col_left:
    st.markdown("#### 📡 News seed")
    seed = st.text_area(
        label="seed",
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

    def stage(slot, label, state="pending"):
        icon = {"pending": "🔘", "active": "🔵", "done": "✅", "error": "❌"}
        slot.markdown(f"{icon.get(state, '🔘')} **{label}**")

    stage(s1, "Article — Perplexity sonar-pro + web search")
    stage(s2, "Newsletters & socials — Perplexity sonar")


# ── Pipeline execution ────────────────────────────────────────────

if run and seed.strip():
    st.session_state.generation_ready = False
    st.session_state.push_success = False

    with col_right:
        with st.status("⚙️ Building asset cluster...", expanded=True) as status:
            try:
                stage(s1, "Article — Perplexity sonar-pro + web search", "active")
                status.update(label="✍️ Stage 1: Researching and writing article via Perplexity...")
                article = generate_article(seed)
                st.session_state.active_title   = article.get("title", "Untitled")
                st.session_state.active_content = article.get("main_content", "")
                stage(s1, "Article — Perplexity sonar-pro + web search", "done")

                stage(s2, "Newsletters & socials — Perplexity sonar", "active")
                status.update(label="📣 Stage 2: Writing newsletters and social copy...")
                dist = generate_distribution(
                    st.session_state.active_title,
                    st.session_state.active_content
                )
                st.session_state.dist_data = dist
                stage(s2, "Newsletters & socials — Perplexity sonar", "done")

                st.session_state.generation_ready = True
                status.update(label="✅ All assets ready — review below.", state="complete", expanded=False)

            except Exception as err:
                status.update(label=f"❌ Pipeline error: {err}", state="error")
                st.error(str(err))


# ── Preview & push ────────────────────────────────────────────────

if st.session_state.generation_ready:
    with col_right:

        if st.session_state.push_success:
            st.markdown(
                '<div class="push-success">🏆 Draft successfully pushed to WordPress!</div>',
                unsafe_allow_html=True
            )

        st.markdown(
            f'<div class="title-banner">📌 {st.session_state.active_title}</div>',
            unsafe_allow_html=True
        )

        if st.button("🔌 Push to WordPress Drafts",
                     type="secondary", use_container_width=True):
            with st.spinner("Pushing draft to WordPress..."):
                success = push_to_wordpress(
                    st.session_state.active_title,
                    st.session_state.active_content,
                    st.session_state.dist_data
                )
                if success:
                    st.session_state.push_success = True
                    st.balloons()
                    st.rerun()

        st.markdown("---")

        tab_art, tab_nl, tab_soc = st.tabs([
            "📝 Article", "📧 Newsletters", "💼 Socials"
        ])

        with tab_art:
            st.markdown(st.session_state.active_content, unsafe_allow_html=True)

        with tab_nl:
            dist = st.session_state.dist_data or {}
            st.markdown("**📬 Substack / WordPress.com**")
            st.code(dist.get("substack_text", ""), language="text")
            st.markdown("---")
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
