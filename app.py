import streamlit as st
import json
import base64
import requests
import re
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

Output ONLY a valid JSON object — no markdown fences, no preamble, no citation markers.
CRITICAL: Do NOT escape quotes or characters inside JSON string values. Write natural text. Output clean JSON only.
{
  "title": "H1 Headline Here",
  "main_content": "Full WordPress HTML content here with \" escaped quotes and \\n newlines"
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
- Include a mini data breakdown using plain numbers and → arrows only
- Reference specific companies, developers, government bodies, and architects involved
- Build genuine tension or intrigue — make people want to read the full piece
- End with one sharp insight or question, then on a new line: "👇 Link to full article analysis in the first comment."
- Aim for 200-250 words maximum
- CRITICAL FORMATTING: Do NOT use asterisks (*) for bold. Do NOT use dashes (-) as bullet points. Use plain text only with line breaks and → arrows.
- NO generic buzzwords. NO "game-changer". NO "exciting opportunity".

FACEBOOK VARIANT:
- Community investor tone, warm and approachable
- Short paragraphs, no bullet points
- End with an engaging question to drive comments
- Include a block of relevant hashtags at the bottom
- CRITICAL FORMATTING: Do NOT use asterisks (*). Do NOT use dashes (-) as bullet points. Plain text with line breaks only.

X / TWITTER: Punchy hook-first post under 280 chars with 1-2 hashtags. No asterisks. No dashes.

INSTAGRAM VARIANT:
- Hook first line that stops the scroll
- 5-8 short punchy lines, each on its own line
- Visual and aspirational tone — paint a picture of the investment opportunity
- End with a call to action: "Link in bio for the full analysis."
- Include 10-15 highly relevant hashtags on a separate line at the bottom
- No asterisks. No dashes as bullets. Use emojis sparingly for visual breaks.

PINTEREST VARIANT:
- SEO-optimised description of 2-3 sentences
- Include the key yield figure, location, and investment type
- End with a call to action
- No asterisks. No dashes.

INSTAGRAM IMAGE PROMPT:
- Write a detailed prompt for generating a cinematic 4:5 vertical Instagram cover image
- Magazine-style real estate editorial composition
- Layered cityscape or property panels, dramatic contrast
- Bold dark gradient bar across lower third
- Large bold headline typography in the foreground, key words in blue and white
- Photorealistic, high-resolution, premium investment media look
- Include the specific location and property type from the article

Output ONLY a valid JSON object — no markdown fences, no preamble, no citation markers.
CRITICAL: Do NOT escape quotes or characters inside JSON string values. Write natural text. Output clean JSON only.
{
  "substack_text": "...",
  "medium_text": "...",
  "linkedin_copy": "...",
  "x_copy": "...",
  "facebook_copy": "...",
  "instagram_copy": "...",
  "pinterest_copy": "...",
  "instagram_image_prompt": "..."
}
"""

SEO_PROMPT = """
You are an expert SEO specialist for PropertyAcross.com.
Given the article title and content below, generate three SEO fields.

RULES:
- seo_title: Maximum 60 characters. Compelling, keyword-rich, includes the primary location and asset type. No clickbait.
- seo_description: Maximum 155 characters. One punchy sentence summarising the investment opportunity and key data point. Must make someone want to click.
- seo_tags: 8-12 comma-separated keyword tags. Mix of broad terms (e.g. real estate investment 2026) and specific micro-topic terms (e.g. Park City commercial property yield). No hashtags, no quotes around individual tags.

Output ONLY a valid JSON object — no markdown fences, no preamble, no citation markers.
CRITICAL: Do NOT escape quotes or characters inside JSON string values. Write natural text. Output clean JSON only.
{
  "seo_title": "Max 60 char SEO title here",
  "seo_description": "Max 155 char meta description here",
  "seo_tags": "tag one, tag two, tag three, tag four"
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
            "active_content", "dist_data", "seo_data", "instagram_copy",
            "instagram_image_prompt"]:
    if key not in st.session_state:
        st.session_state[key] = False if key in ["generation_ready", "push_success"] else None


# ── Pipeline functions ────────────────────────────────────────────

def strip_citations(text: str) -> str:
    """Remove Perplexity citation markers and unescape JSON-escaped characters."""
    text = re.sub(r'(\[\d+\])+', '', text)
    text = text.replace('\"', '"').replace("\'", "'")
    text = text.replace('\\n', '\n').replace('\\t', '\t')
    return text.strip()


def strip_formatting(text: str) -> str:
    """Remove asterisks and dash bullets from social copy."""
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'(?m)^\s*-\s+', '', text)
    return text.strip()


def call_perplexity(messages: list, model: str = "sonar-pro") -> str:
    if not PERPLEXITY_API_KEY:
        raise Exception("PERPLEXITY_API_KEY is missing from secrets.")
    enforced_messages = messages.copy()
    enforced_messages[0]["content"] = enforced_messages[0]["content"] + "\n\nABSOLUTE RULE: Your entire response must be a single valid JSON object. No text before it. No text after it. No explanations. No markdown. Start with { and end with }."
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": enforced_messages,
                "temperature": 0.2,
                "max_tokens": 8000,
            },
            timeout=120
        )
    except requests.exceptions.Timeout:
        raise Exception("Perplexity API timed out after 120 seconds. Try again.")
    except requests.exceptions.ConnectionError:
        raise Exception("Could not connect to Perplexity API. Check network.")

    if response.status_code != 200:
        raise Exception(f"Perplexity API error ({response.status_code}): {response.text[:300]}")

    data = response.json()
    if "choices" not in data or not data["choices"]:
        raise Exception(f"Unexpected Perplexity response structure: {str(data)[:300]}")

    return data["choices"][0]["message"]["content"]


def safe_parse_json(text: str) -> dict:
    """
    Robustly extract and parse JSON from Perplexity responses.
    Handles unescaped quotes, stray newlines, and markdown fences.
    """
    # Strip markdown fences if present
    text = re.sub(r'```json|```', '', text).strip()

    # Extract outermost { ... } block
    s, e = text.find('{'), text.rfind('}')
    if s == -1 or e == -1:
        raise ValueError("No JSON object found in response.")
    text = text[s:e+1]

    # First attempt: parse as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Second attempt: try to fix common issues and parse again
    try:
        # Replace smart quotes with regular quotes
        fixed = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Third attempt: use regex to extract each key-value pair individually
    result = {}
    pattern = re.compile(
        r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"',
        re.DOTALL
    )
    for match in pattern.finditer(text):
        key = match.group(1)
        value = match.group(2)
        value = value.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
        result[key] = value

    if result:
        return result

    # Last resort: show raw response in Streamlit for debugging
    st.error(f"Raw Perplexity response (first 500 chars):\n{text[:500]}")
    raise ValueError(f"Could not parse JSON from response.")


def generate_article(raw_input: str) -> dict:
    # Step 1: Generate title only (small, fast)
    title_messages = [
        {"role": "system", "content": (
            "You are an SEO expert for PropertyAcross.com. "
            "Given the news seed, return ONLY a single valid JSON object with one key: title. "
            "The title must be a bold question-based H1 headline targeting real estate investors in 2026. "
            "Example: {\"title\": \"Will Athens Fractional Studios Deliver 6% Yields for Golden Visa Buyers in 2026?\"} "
            "ABSOLUTE RULE: Return only the JSON object. Nothing else."
        )},
        {"role": "user", "content": f"News seed:\n{raw_input}"}
    ]
    title_text = call_perplexity(title_messages, model="sonar")
    title_result = safe_parse_json(title_text)
    title = strip_citations(title_result.get("title", "Untitled"))

    # Step 2: Generate article body as plain HTML (no JSON wrapper, uses full token budget)
    body_messages = [
        {"role": "system", "content": (
            "You are the Lead SEO Architect for PropertyAcross.com. "
            "Using live web search, write a 1,200+ word evidence-based real estate investment article in clean WordPress HTML. "
            "Rules: "
            "1. Use question-based H2/H3 subheadings focused on investor concerns. "
            "2. Under each heading write 2-4 short paragraphs with hard statistics, yield figures, and price points. "
            "3. Every claim must be backed by a concrete number or data point. "
            "4. End with an FAQ block of 5-7 high-volume Q&As. "
            "5. Use only these HTML tags: h2, h3, p, strong, ul, li. Do NOT use h1. "
            "6. Output ONLY the raw HTML. No JSON. No markdown. No preamble. No citation markers like [1][2]."
        )},
        {"role": "user", "content": f"Article title: {title}\n\nNews seed: {raw_input}"}
    ]
    body_text = call_perplexity(body_messages, model="sonar-pro")
    main_content = strip_citations(body_text.strip())

    # Wrap with H1
    main_content = f"<h1>{title}</h1>\n" + main_content

    return {"title": title, "main_content": main_content}


def generate_distribution(title: str, content: str) -> dict:
    messages = [
        {"role": "system", "content": NEWSLETTER_PROMPT},
        {"role": "user",   "content": f"Article title: {title}\n\nFull article content:\n{content}"}
    ]
    text = call_perplexity(messages, model="sonar")
    result = safe_parse_json(text)
    if isinstance(result, list):
        result = result[0]
    cleaned = {}
    for k, v in result.items():
        if isinstance(v, str):
            v = strip_citations(v)
            if k in ["linkedin_copy", "facebook_copy", "instagram_copy", "x_copy", "pinterest_copy"]:
                v = strip_formatting(v)
        cleaned[k] = v
    return cleaned


def generate_seo(title: str, content: str) -> dict:
    messages = [
        {"role": "system", "content": SEO_PROMPT},
        {"role": "user",   "content": f"Article title: {title}\n\nArticle content:\n{content[:3000]}"}
    ]
    text = call_perplexity(messages, model="sonar")
    result = safe_parse_json(text)
    if isinstance(result, list):
        result = result[0]
    # Enforce character limits hard
    seo_title = strip_citations(result.get("seo_title", ""))[:60]
    seo_desc  = strip_citations(result.get("seo_description", ""))[:155]
    seo_tags  = strip_citations(result.get("seo_tags", ""))
    return {
        "seo_title":       seo_title,
        "seo_description": seo_desc,
        "seo_tags":        seo_tags,
    }


def push_to_wordpress(title: str, content: str, dist: dict, seo: dict) -> bool:
    url = f"{WP_URL}/posts"
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }
    payload = {
        "title":   title,
        "content": content,
        "status":  "draft",
        "meta": {
            "substack_text":        dist.get("substack_text", ""),
            "medium_text":          dist.get("medium_text", ""),
            "linkedin_copy":        dist.get("linkedin_copy", ""),
            "x_copy":               dist.get("x_copy", ""),
            "facebook_copy":        dist.get("facebook_copy", ""),
            "instagram_copy":       dist.get("instagram_copy", ""),
            "pinterest_copy":       dist.get("pinterest_copy", ""),
            "instagram_image_prompt": dist.get("instagram_image_prompt", ""),
            "_yoast_wpseo_title":   seo.get("seo_title", ""),
            "_yoast_wpseo_metadesc":seo.get("seo_description", ""),
            "rank_math_focus_keyword": seo.get("seo_tags", ""),
            "_yoast_wpseo_focuskw": seo.get("seo_tags", "").split(",")[0].strip() if seo.get("seo_tags") else "",
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
    s3 = st.empty()

    def stage(slot, label, state="pending"):
        icon = {"pending": "🔘", "active": "🔵", "done": "✅", "error": "❌"}
        slot.markdown(f"{icon.get(state, '🔘')} **{label}**")

    stage(s1, "Article — Perplexity sonar-pro + web search")
    stage(s2, "Newsletters & socials — Perplexity sonar")
    stage(s3, "SEO title, description & tags — Perplexity sonar")


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

                stage(s3, "SEO title, description & tags — Perplexity sonar", "active")
                status.update(label="🔍 Stage 3: Generating SEO fields...")
                seo = generate_seo(
                    st.session_state.active_title,
                    st.session_state.active_content
                )
                st.session_state.seo_data = seo
                stage(s3, "SEO title, description & tags — Perplexity sonar", "done")

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
                    st.session_state.dist_data,
                    st.session_state.seo_data or {}
                )
                if success:
                    st.session_state.push_success = True
                    st.balloons()
                    st.rerun()

        st.markdown("---")

        tab_art, tab_nl, tab_soc, tab_seo = st.tabs([
            "📝 Article", "📧 Newsletters", "💼 Socials", "🔍 SEO"
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
            st.markdown("**📸 Instagram**")
            st.text(dist.get("instagram_copy", ""))
            st.markdown("---")
            st.markdown("**📌 Pinterest**")
            st.text(dist.get("pinterest_copy", ""))
            st.markdown("---")
            st.markdown("**🖼️ Instagram Image Prompt**")
            st.code(dist.get("instagram_image_prompt", ""), language="text")

        with tab_seo:
            seo = st.session_state.seo_data or {}

            st.markdown("**🏷️ SEO Title**")
            seo_title = seo.get("seo_title", "")
            st.code(seo_title, language="text")
            char_count = len(seo_title)
            colour = "green" if char_count <= 60 else "red"
            st.markdown(f":{colour}[{char_count}/60 characters]")

            st.markdown("---")
            st.markdown("**📄 Meta Description**")
            seo_desc = seo.get("seo_description", "")
            st.code(seo_desc, language="text")
            char_count2 = len(seo_desc)
            colour2 = "green" if char_count2 <= 155 else "red"
            st.markdown(f":{colour2}[{char_count2}/155 characters]")

            st.markdown("---")
            st.markdown("**🔖 SEO Tags**")
            seo_tags = seo.get("seo_tags", "")
            st.code(seo_tags, language="text")
            tag_list = [t.strip() for t in seo_tags.split(",") if t.strip()]
            st.markdown(f"*{len(tag_list)} tags generated*")
