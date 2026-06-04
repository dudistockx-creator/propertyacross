import streamlit as st
import json
import base64
import requests
import re
from datetime import date, datetime
from dotenv import load_dotenv
import os

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
WP_URL             = os.getenv("WP_URL", "")
WP_USERNAME        = os.getenv("WP_USERNAME", "admin")
WP_APP_PASSWORD    = os.getenv("WP_APP_PASSWORD", "")

# ── News Discovery Prompt ─────────────────────────────────────────

NEWS_DISCOVERY_PROMPT = """
You are a global real estate news intelligence agent for PropertyAcross.com.

Search the web RIGHT NOW for real estate news published in the LAST 8 HOURS only.
Today's date is {today}. Only return articles from {today}. Reject anything older.

REGIONS TO COVER (at least 2-3 stories per major region):
- United States & Canada
- Western Europe (UK, France, Germany, Spain, Portugal, Italy, Netherlands)
- Central & Eastern Europe (Poland, Czech Republic, Hungary, Romania, Serbia, Greece, Cyprus)
- Caucasus & Central Asia (Georgia, Armenia, Azerbaijan, Kazakhstan, UAE, Saudi Arabia, Turkey)
- Africa (South Africa, Nigeria, Kenya, Egypt, Morocco)
- South East Asia (Thailand, Vietnam, Indonesia, Philippines, Malaysia, Singapore)
- Far East & APAC (Japan, South Korea, China, Hong Kong, Australia, New Zealand)
- LATAM (Brazil, Mexico, Colombia, Argentina, Chile, Panama)

ASSET SUBCATEGORIES TO COVER:
RESIDENTIAL: Low & High Rise Apartments, Studio Apartments, Condominiums, Townhouses,
Student Housing, Senior Living, Luxury Villas, Serviced Apartments
COMMERCIAL: Retail Spaces, Office Spaces, Hospitality, Co-Working Spaces
INDUSTRIAL: Warehouses & Logistics, Self-Storage Units, Data Centers
CITIZENSHIP BY INVESTMENT: Caribbean CBI, European CBI, Asian CBI, MENA CBI
TOKENIZED REAL ESTATE: Tokenized Pre-Construction, Tokenized Commercial, Fractional Ownership

RULES:
- Minimum 20 news items total
- NO property listings (for sale / for rent ads) — news only
- Include non-English sources — translate title and description to English, keep original URL
- Research each story fully before returning it — do not summarise in 2 sentences
- title: Specific and informative — include city, asset type, and key angle (e.g. "Lisbon Developer Vanguard Launches 320-Unit BTR Tower Targeting 6.2% Yield")
- description: 4-6 sentences covering ALL of the following that are relevant:
    1. What happened: deal, launch, acquisition, funding round, policy change, project announcement
    2. Investment / project value in local currency AND USD equivalent
    3. Developer name(s): full company name, country of origin, notable past projects
    4. Architect / design firm name if mentioned or findable via web search
    5. City administration or government body involved: permits, zoning, incentives, CBI program name
    6. Financial data: yield figures, price per sqm, rental rates, occupancy rates
    7. Timeline: construction start, completion date, delivery phases
    8. Buyer / tenant profile: institutional investors, retail buyers, expats, tech firms, etc.
- Prioritise stories with named companies, deal values, yield figures, and government involvement

URL INTEGRITY — THIS IS CRITICAL — READ CAREFULLY:
- ONLY return URLs that were directly retrieved and confirmed in your live web search results this session
- NEVER construct, guess, or infer a URL — even if you know the publisher's domain well
- NEVER return a homepage or section URL (e.g. bloomberg.com or reuters.com/markets) — only exact article URLs
- NEVER fabricate or approximate a URL path — if you are not 100% certain the URL exists, do not include it
- If you cannot find a verified, clickable article URL for a story, DROP that story entirely — do not include it with a guessed URL
- Include a "source" field with the real publication name (e.g. "Bloomberg", "Reuters", "The National", "Bangkok Post")
- Each URL must be from a recognised news outlet, industry publication, or official government/company press release
- Before including any item, ask yourself: "Did my search engine actually return this exact URL?" — if the answer is no, exclude the item

Output ONLY a valid JSON array — no markdown fences, no preamble:
[
  {{
    "title": "Specific title with city + asset type + key angle",
    "description": "4-6 sentences: deal details, developer, architect, city/government body, yield/price data, timeline, buyer profile.",
    "url": "https://exact-article-url-from-search-results.com/article/slug",
    "source": "Publication name e.g. Reuters, Bloomberg, The National",
    "date": "{today}",
    "region": "Western Europe",
    "asset_category": "COMMERCIAL — Office Spaces",
    "developer": "Full developer / company name(s) or N/A",
    "architect": "Architect or design firm or N/A",
    "city_body": "Government / municipal body or N/A",
    "deal_value": "Value in local currency + USD equivalent or N/A"
  }}
]
"""

# ── Article / Distribution / SEO Prompts ─────────────────────────

NEWSLETTER_PROMPT = """
You are a world-class financial newsletter writer for PropertyAcross.com.
Your writing style sits between The Economist's precision and Morning Brew's readability.

Given the article title and full content below, produce distribution copy for all channels.

SUBSTACK / WORDPRESS.COM VARIANT: 350-450 words, personal investor note style, bold key data, "Why this matters right now" section, end with a question.

MEDIUM VARIANT: 500-600 word polished financial essay, [PULL-QUOTE: "..."] tags on 2-3 insights, hook → context → analysis → outlook → CTA.

LINKEDIN VARIANT: 200-250 words, staccato lines, lead with surprising data, → arrows for breakdowns, end with insight + "👇 Link to full article analysis in the first comment." NO asterisks. NO dashes as bullets.

FACEBOOK VARIANT: Warm community tone, short paragraphs, no bullets/asterisks/dashes, end with question, hashtags at bottom.

X / TWITTER: Under 280 chars, hook-first, 1-2 hashtags. No asterisks.

INSTAGRAM VARIANT: Hook first line, 5-8 short lines each on own line, aspirational tone, end with "Link in bio for the full analysis.", 10-15 hashtags on separate line. No asterisks. No dashes.

PINTEREST VARIANT: 2-3 sentence SEO description, key yield/location/type, CTA. No asterisks.

INSTAGRAM IMAGE PROMPT: Detailed cinematic 4:5 vertical Instagram cover — magazine-style real estate editorial, layered cityscape panels, dramatic contrast, bold dark gradient bar lower third, large bold headline typography, key words in blue and white, photorealistic premium look.

Output ONLY a valid JSON object — no markdown fences, no preamble:
{{
  "substack_text": "...",
  "medium_text": "...",
  "linkedin_copy": "...",
  "x_copy": "...",
  "facebook_copy": "...",
  "instagram_copy": "...",
  "pinterest_copy": "...",
  "instagram_image_prompt": "..."
}}
"""

SEO_PROMPT = """
You are an expert SEO specialist for PropertyAcross.com.
Given the article title and content, generate three SEO fields.

- seo_title: Maximum 60 characters. Write like a headline editor at The Economist — punchy, specific, intriguing. Lead with the most surprising number or angle. Include location + asset type naturally. Must make someone stop scrolling. No generic phrases like "Guide to" or "Everything About". No clickbait. Examples of good style: "Athens Studios: 6.8% Yield Beats London by 3x" or "Why Dubai Data Centers Outperform Apartments in 2026".
- seo_description: Maximum 155 characters. One punchy sentence with key data point. Makes people click.
- seo_tags: 8-12 comma-separated keyword tags. Mix broad + micro-topic. No hashtags.

Output ONLY a valid JSON object — no markdown fences, no preamble:
{{
  "seo_title": "Max 60 char SEO title here",
  "seo_description": "Max 155 char meta description here",
  "seo_tags": "tag one, tag two, tag three"
}}
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
    .news-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #1a3c6b;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 8px;
    }
    .region-badge {
        display: inline-block;
        background: #e8f0fe;
        color: #1a3c6b;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 20px;
        margin-right: 6px;
    }
    .cat-badge {
        display: inline-block;
        background: #fef3c7;
        color: #92400e;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 20px;
    }
    .news-title { font-size: 13px; font-weight: 600; color: #1a202c; margin: 6px 0 3px 0; }
    .news-desc  { font-size: 12px; color: #4a5568; margin: 0 0 5px 0; line-height: 1.4; }
    .news-url   { font-size: 11px; color: #2b6cb0; }
    .fetch-info { font-size: 12px; color: #718096; margin-bottom: 8px; }
    .meta-pill  {
        display: inline-block;
        font-size: 11px; font-weight: 500;
        padding: 2px 8px; border-radius: 20px;
        margin-right: 5px; margin-bottom: 4px;
    }
    .dev-pill   { background: #e0f2fe; color: #0369a1; }
    .arch-pill  { background: #f3e8ff; color: #7e22ce; }
    .city-pill  { background: #dcfce7; color: #166534; }
    .val-pill   { background: #fff7ed; color: #c2410c; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────

_defaults = {
    "generation_ready": False,
    "push_success": False,
    "active_title": None,
    "active_content": None,
    "dist_data": None,
    "seo_data": None,
    "news_items": None,
    "news_fetched_at": None,
    "selected_indices": [],
    "generation_source": None,
    "current_batch": [],
    "batch_index": 0,
    "batch_results": [],
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Pipeline helpers ──────────────────────────────────────────────

def strip_citations(text: str) -> str:
    text = re.sub(r'(\[\d+\])+', '', text)
    text = text.replace('\\n', '\n').replace('\\t', '\t')
    return text.strip()

def strip_formatting(text: str) -> str:
    text = re.sub(r'[*]+', '', text)
    text = re.sub(r'(?m)^\s*[-]\s+', '', text)
    return text.strip()

def call_perplexity(messages: list, model: str = "sonar-pro") -> str:
    if not PERPLEXITY_API_KEY:
        raise Exception("PERPLEXITY_API_KEY is missing from .env / secrets.")
    msgs = messages.copy()
    msgs[0]["content"] += (
        "\n\nABSOLUTE RULE: Your entire response must be a single valid JSON object or array. "
        "No text before it. No text after it. No markdown fences. Start with { or [ and end with } or ]."
    )
    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": msgs, "temperature": 0.2, "max_tokens": 8000},
            timeout=120
        )
    except requests.exceptions.Timeout:
        raise Exception("Perplexity API timed out after 120s. Try again.")
    except requests.exceptions.ConnectionError:
        raise Exception("Could not connect to Perplexity API. Check network.")

    if r.status_code != 200:
        raise Exception(f"Perplexity API error ({r.status_code}): {r.text[:300]}")

    data = r.json()
    if "choices" not in data or not data["choices"]:
        raise Exception(f"Unexpected Perplexity response: {str(data)[:300]}")
    return data["choices"][0]["message"]["content"]

def safe_parse_json(text: str):
    text = re.sub(r'```json|```', '', text).strip()
    if text.lstrip().startswith('['):
        s, e = text.find('['), text.rfind(']')
        if s != -1 and e != -1:
            try:
                return json.loads(text[s:e+1])
            except Exception:
                pass
    s, e = text.find('{'), text.rfind('}')
    if s == -1 or e == -1:
        raise ValueError("No JSON found in response.")
    chunk = text[s:e+1]
    try:
        return json.loads(chunk)
    except Exception:
        pass
    fixed = chunk.replace('\u201c','"').replace('\u201d','"').replace('\u2018',"'").replace('\u2019',"'")
    try:
        return json.loads(fixed)
    except Exception:
        pass
    result = {}
    for m in re.finditer(r'"(\w+)"\s*:\s*"((?:[^"\\]|\\.)*)"', chunk, re.DOTALL):
        result[m.group(1)] = m.group(2).replace('\\"','"').replace('\\n','\n')
    if result:
        return result
    raise ValueError(f"Could not parse JSON. Raw: {text[:400]}")

def fetch_news_seeds() -> list:
    """Fetch real estate news via Perplexity sonar-pro with live web search."""
    today_str = date.today().strftime("%Y-%m-%d")
    prompt = NEWS_DISCOVERY_PROMPT.replace("{today}", today_str)
    msgs = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": (
            f"Search the web right now for real estate news published today {today_str}. "
            "Return at least 20 items across all regions and categories. "
            "Exclude listings. Translate non-English sources to English. "
            "Every URL must be a real article link you actually retrieved — "
            "if you cannot confirm a URL exists, exclude that story entirely. "
            "Return ONLY the JSON array."
        )}
    ]
    text = call_perplexity(msgs, model="sonar-pro")
    result = safe_parse_json(text)
    if isinstance(result, list):
        return result
    for v in result.values():
        if isinstance(v, list):
            return v
    return []

def generate_article(raw_input: str) -> dict:
    # Step 1: title
    title_r = safe_parse_json(call_perplexity([
        {"role": "system", "content": (
            "You are an SEO expert for PropertyAcross.com. "
            "Return ONLY: {\"title\": \"Bold question-based H1 headline for real estate investors 2026\"}"
        )},
        {"role": "user", "content": f"News seed:\n{raw_input}"}
    ], model="sonar"))
    title = strip_citations(title_r.get("title", "Untitled"))

    # Step 2: body
    body_text = call_perplexity([
        {"role": "system", "content": (
            "You are the Lead SEO Architect for PropertyAcross.com writing for serious real estate investors. "
            "Use live web search for current statistics, yields, and price data.\n\n"
            "STRUCTURE:\n"
            "1. Opening intro (50-80 words): inverted pyramid, key data point first.\n"
            "2. Key Takeaways: <strong>Key Takeaways</strong> then <ul> with 3-4 bullets.\n"
            "3. H2/H3 subheadings as investor questions.\n"
            "4. Under each: 2-3 paragraphs (80-120 words each), active voice.\n"
            "5. Every claim: named source inline (e.g. 'according to Knight Frank'). No [1][2] markers.\n"
            "6. FAQ: 5-7 Q&A, 40-60 words each, snippet-optimised.\n"
            "7. Closing CTA (40-60 words): summarise + point to PropertyAcross.com.\n\n"
            "TONE: Senior investment bank analyst. No fluff. Hard numbers only. Active voice.\n"
            "FORBIDDEN: 'booming', 'thriving', 'exciting', 'in today's market', 'it is worth noting'.\n"
            "HTML ONLY: h2, h3, p, strong, ul, li. No h1. No inline styles. No tables. No divs.\n"
            "Output ONLY raw HTML. No JSON wrapper. No markdown. No citation markers."
        )},
        {"role": "user", "content": f"Article title: {title}\n\nNews seed: {raw_input}"}
    ], model="sonar-pro")

    main_content = f"<h1>{title}</h1>\n" + strip_citations(body_text.strip())
    return {"title": title, "main_content": main_content}

def generate_distribution(title: str, content: str) -> dict:
    text = call_perplexity([
        {"role": "system", "content": NEWSLETTER_PROMPT},
        {"role": "user",   "content": f"Article title: {title}\n\nFull article content:\n{content}"}
    ], model="sonar")
    result = safe_parse_json(text)
    if isinstance(result, list):
        result = result[0]
    cleaned = {}
    for k, v in result.items():
        if isinstance(v, str):
            v = strip_citations(v)
            if k in ["linkedin_copy","facebook_copy","instagram_copy","x_copy","pinterest_copy"]:
                v = strip_formatting(v)
        cleaned[k] = v
    return cleaned

def generate_seo(title: str, content: str) -> dict:
    text = call_perplexity([
        {"role": "system", "content": SEO_PROMPT},
        {"role": "user",   "content": f"Article title: {title}\n\nContent:\n{content[:3000]}"}
    ], model="sonar")
    result = safe_parse_json(text)
    if isinstance(result, list):
        result = result[0]
    return {
        "seo_title":       strip_citations(result.get("seo_title", ""))[:60],
        "seo_description": strip_citations(result.get("seo_description", ""))[:155],
        "seo_tags":        strip_citations(result.get("seo_tags", "")),
    }

def get_or_create_wp_tags(tag_names: list, headers: dict) -> list:
    """Look up existing WP tags by name, create missing ones. Returns list of tag IDs."""
    tag_ids = []
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        try:
            # Search for existing tag
            r = requests.get(
                f"{WP_URL}/tags",
                headers=headers,
                params={"search": name, "per_page": 5},
                timeout=15
            )
            if r.status_code == 200:
                matches = [t for t in r.json() if t.get("name","").lower() == name.lower()]
                if matches:
                    tag_ids.append(matches[0]["id"])
                    continue
            # Create new tag
            r2 = requests.post(
                f"{WP_URL}/tags",
                headers=headers,
                json={"name": name},
                timeout=15
            )
            if r2.status_code == 201:
                tag_ids.append(r2.json()["id"])
        except Exception:
            continue  # Skip tag silently on error
    return tag_ids


def push_to_wordpress(title: str, content: str, dist: dict, seo: dict) -> bool:
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    # Resolve tag names → WP tag IDs
    raw_tags   = seo.get("seo_tags", "")
    tag_names  = [t.strip() for t in raw_tags.split(",") if t.strip()]
    tag_ids    = get_or_create_wp_tags(tag_names, headers) if tag_names else []
    focus_kw   = tag_names[0] if tag_names else ""

    payload = {
        "title":   title,
        "content": content,
        "status":  "draft",
        "tags":    tag_ids,          # ← WordPress native tags taxonomy
        "meta": {
            # Distribution copy
            "substack_text":  dist.get("substack_text", ""),
            "medium_text":    dist.get("medium_text", ""),
            "linkedin_copy":  dist.get("linkedin_copy", ""),
            "x_copy":         dist.get("x_copy", ""),
            "facebook_copy":  dist.get("facebook_copy", ""),
            "pinterest_copy": dist.get("pinterest_copy", ""),
            # Yoast SEO fields
            "_yoast_wpseo_title":    seo.get("seo_title", ""),
            "_yoast_wpseo_metadesc": seo.get("seo_description", ""),
            "_yoast_wpseo_focuskw":  focus_kw,
            # Rank Math fields
            "rank_math_title":           seo.get("seo_title", ""),
            "rank_math_description":     seo.get("seo_description", ""),
            "rank_math_focus_keyword":   focus_kw,
            # All tags as comma string (fallback for custom SEO plugins)
            "seo_tags":                  raw_tags,
        }
    }

    try:
        r = requests.post(f"{WP_URL}/posts", headers=headers, json=payload, timeout=45)
        if r.status_code == 201:
            post_id = r.json().get("id", "?")
            st.caption(f"WordPress post ID: {post_id} | Tags applied: {len(tag_ids)}/{len(tag_names)}")
            return True
        st.error(f"WordPress push failed ({r.status_code}): {r.text[:300]}")
    except Exception as e:
        st.error(f"WordPress connection error: {e}")
    return False

def render_results_tabs(key_suffix: str = ""):
    """Render the article preview + push button. Call after pipeline completes."""
    if st.session_state.push_success:
        st.markdown('<div class="push-success">🏆 Draft successfully pushed to WordPress!</div>',
                    unsafe_allow_html=True)

    st.markdown(f'<div class="title-banner">📌 {st.session_state.active_title}</div>',
                unsafe_allow_html=True)

    if st.button("🔌 Push to WordPress Drafts", type="secondary",
                 use_container_width=True, key=f"wp_push_{key_suffix}"):
        with st.spinner("Pushing to WordPress..."):
            ok = push_to_wordpress(
                st.session_state.active_title,
                st.session_state.active_content,
                st.session_state.dist_data or {},
                st.session_state.seo_data or {}
            )
            if ok:
                st.session_state.push_success = True
                st.balloons()
                st.rerun()

    st.markdown("---")
    tab_art, tab_nl, tab_soc, tab_seo = st.tabs(["📝 Article","📧 Newsletters","💼 Socials","🔍 SEO"])

    with tab_art:
        st.markdown(st.session_state.active_content or "", unsafe_allow_html=True)

    with tab_nl:
        dist = st.session_state.dist_data or {}
        st.markdown("**📬 Substack / WordPress.com**")
        st.code(dist.get("substack_text",""), language="text")
        st.markdown("---")
        st.markdown("**📘 Medium**")
        st.code(dist.get("medium_text",""), language="text")

    with tab_soc:
        dist = st.session_state.dist_data or {}
        st.markdown("**💼 LinkedIn**")
        st.text(dist.get("linkedin_copy",""))
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🐦 X / Twitter**")
            st.info(dist.get("x_copy",""))
        with c2:
            st.markdown("**👥 Facebook**")
            st.text(dist.get("facebook_copy",""))
        st.markdown("---")
        st.markdown("**📸 Instagram**")
        st.text(dist.get("instagram_copy",""))
        st.markdown("---")
        st.markdown("**📌 Pinterest**")
        st.text(dist.get("pinterest_copy",""))
        st.markdown("---")
        st.markdown("**🖼️ Instagram Image Prompt**")
        st.code(dist.get("instagram_image_prompt",""), language="text")

    with tab_seo:
        seo = st.session_state.seo_data or {}
        st.markdown("**🏷️ SEO Title**")
        seo_title = seo.get("seo_title","")
        st.code(seo_title, language="text")
        c = len(seo_title)
        st.markdown(f":{'green' if c<=60 else 'red'}[{c}/60 characters]")
        st.markdown("---")
        st.markdown("**📄 Meta Description**")
        seo_desc = seo.get("seo_description","")
        st.code(seo_desc, language="text")
        c2 = len(seo_desc)
        st.markdown(f":{'green' if c2<=155 else 'red'}[{c2}/155 characters]")
        st.markdown("---")
        st.markdown("**🔖 SEO Tags**")
        seo_tags = seo.get("seo_tags","")
        st.code(seo_tags, language="text")
        tags = [t.strip() for t in seo_tags.split(",") if t.strip()]
        st.markdown(f"*{len(tags)} tags generated*")


# ── UI ────────────────────────────────────────────────────────────

st.title("🏢 PropertyAcross Content Studio")
st.caption("Perplexity-powered research · WordPress push")
st.markdown("---")

main_tab_news, main_tab_manual = st.tabs([
    "🌍 News Discovery  ←  Start Here", "✏️ Manual Seed"
])

# ════════════════════════════════════════════════════════════════
# TAB 1 — NEWS DISCOVERY
# ════════════════════════════════════════════════════════════════

with main_tab_news:
    col_left, col_right = st.columns([1, 1.4], gap="large")

    with col_left:
        st.markdown("#### 🌍 Live Global News Feed")
        st.caption("Fetches the last 8 hours of real estate news worldwide. Select items with checkboxes, then generate.")

        # Fetch button + last-fetch info
        col_btn, col_info = st.columns([2, 3])
        with col_btn:
            fetch_btn = st.button("🔄 Fetch News", type="primary", use_container_width=True)
        with col_info:
            if st.session_state.news_fetched_at:
                st.markdown(
                    f'<div class="fetch-info">Last fetch: {st.session_state.news_fetched_at}<br>'
                    f'{len(st.session_state.news_items or [])} stories loaded</div>',
                    unsafe_allow_html=True
                )

        if fetch_btn:
            with st.spinner("Searching Google News via Gemini — real sources only..."):
                try:
                    items = fetch_news_seeds()
                    st.session_state.news_items = items
                    st.session_state.news_fetched_at = datetime.now().strftime("%H:%M:%S")
                    st.session_state.selected_indices = []
                    st.rerun()
                except Exception as e:
                    st.error(f"News fetch error: {e}")

        # News list with checkboxes
        if st.session_state.news_items:
            items = st.session_state.news_items

            # Filters
            regions = sorted(set(n.get("region","?") for n in items))
            cats    = sorted(set(n.get("asset_category","?") for n in items))
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                sel_region = st.selectbox("Region", ["All"] + regions, key="filter_region")
            with f_col2:
                sel_cat = st.selectbox("Category", ["All"] + cats, key="filter_cat")

            filtered = [
                (i, n) for i, n in enumerate(items)
                if (sel_region == "All" or n.get("region") == sel_region)
                and (sel_cat == "All" or n.get("asset_category") == sel_cat)
            ]

            st.caption(f"Showing {len(filtered)} of {len(items)} stories — tick to select, then Generate")

            # Select all / clear
            sa_col, cl_col = st.columns(2)
            with sa_col:
                if st.button("☑️ Select all visible", use_container_width=True):
                    st.session_state.selected_indices = list(set(
                        st.session_state.selected_indices + [i for i, _ in filtered]
                    ))
                    st.rerun()
            with cl_col:
                if st.button("✖️ Clear selection", use_container_width=True):
                    st.session_state.selected_indices = []
                    st.rerun()

            # News cards with checkboxes
            for orig_idx, item in filtered:
                region     = item.get("region","")
                cat        = item.get("asset_category","")
                title      = item.get("title","No title")
                desc       = item.get("description","")
                url        = item.get("url","")
                source     = item.get("source","")
                developer  = item.get("developer","")
                architect  = item.get("architect","")
                city_body  = item.get("city_body","")
                deal_value = item.get("deal_value","")

                is_checked = orig_idx in st.session_state.selected_indices

                checked = st.checkbox(
                    label=f"**{title}**",
                    value=is_checked,
                    key=f"chk_{orig_idx}"
                )

                if checked and orig_idx not in st.session_state.selected_indices:
                    st.session_state.selected_indices.append(orig_idx)
                elif not checked and orig_idx in st.session_state.selected_indices:
                    st.session_state.selected_indices.remove(orig_idx)

                # Build meta pills for the extra fields
                meta_pills = ""
                if developer and developer != "N/A":
                    meta_pills += f'<span class="meta-pill dev-pill">🏗️ {developer}</span>'
                if architect and architect != "N/A":
                    meta_pills += f'<span class="meta-pill arch-pill">✏️ {architect}</span>'
                if city_body and city_body != "N/A":
                    meta_pills += f'<span class="meta-pill city-pill">🏛️ {city_body}</span>'
                if deal_value and deal_value != "N/A":
                    meta_pills += f'<span class="meta-pill val-pill">💰 {deal_value}</span>'

                st.markdown(
                    f'<div class="news-card" style="margin-top:-8px">'
                    f'<span class="region-badge">🌍 {region}</span>'
                    f'<span class="cat-badge">{cat}</span>'
                    f'<p class="news-desc" style="margin-top:6px">{desc}</p>'
                    f'{("<div style=\"margin-bottom:6px\">" + meta_pills + "</div>") if meta_pills else ""}'
                    f'<a class="news-url" href="{url}" target="_blank">'
                    f'{"📰 " + source + " — " if source else "🔗 "}{url[:60]}{"..." if len(url)>60 else ""}</a>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            # Selection summary + generate button
            n_sel = len(st.session_state.selected_indices)
            if n_sel > 0:
                st.markdown("---")
                st.success(f"**{n_sel} article{'s' if n_sel>1 else ''} selected** — ready to generate")

                if st.button(f"🚀 Generate {n_sel} Article{'s' if n_sel>1 else ''}",
                             type="primary", use_container_width=True, key="generate_selected"):
                    # Build batch seeds
                    batch = []
                    for idx in st.session_state.selected_indices:
                        item = items[idx]
                        extras = []
                        if item.get("developer","") not in ("","N/A"):
                            extras.append(f"Developer: {item['developer']}")
                        if item.get("architect","") not in ("","N/A"):
                            extras.append(f"Architect: {item['architect']}")
                        if item.get("city_body","") not in ("","N/A"):
                            extras.append(f"Government/City body: {item['city_body']}")
                        if item.get("deal_value","") not in ("","N/A"):
                            extras.append(f"Deal value: {item['deal_value']}")
                        extras_str = ("\n" + "\n".join(extras)) if extras else ""
                        seed_text = (
                            f"{item.get('title','')}\n\n"
                            f"{item.get('description','')}"
                            f"{extras_str}\n\n"
                            f"Source: {item.get('url','')}"
                        )
                        batch.append({"seed": seed_text, "item": item})
                    st.session_state.current_batch = batch
                    st.session_state.batch_index   = 0
                    st.session_state.batch_results  = []
                    st.session_state.generation_ready  = False
                    st.session_state.push_success      = False
                    st.session_state.generation_source = "news_discovery"
                    st.rerun()

    # ── Right column: pipeline + results ──
    with col_right:
        st.markdown("#### ⚙️ Pipeline")

        s1 = st.empty()
        s2 = st.empty()
        s3 = st.empty()

        def stage(slot, label, state="pending"):
            icons = {"pending":"🔘","active":"🔵","done":"✅","error":"❌"}
            slot.markdown(f"{icons.get(state,'🔘')} **{label}**")

        stage(s1, "Article — Perplexity sonar-pro + web search")
        stage(s2, "Newsletters & socials — sonar")
        stage(s3, "SEO title, description & tags — sonar")

        # Run batch pipeline
        batch = st.session_state.get("current_batch", [])
        bidx  = st.session_state.get("batch_index", 0)

        if batch and bidx < len(batch) and st.session_state.generation_source == "news_discovery":
            current = batch[bidx]
            total   = len(batch)

            with st.status(
                f"⚙️ Building article {bidx+1} of {total}...", expanded=True
            ) as status:
                try:
                    stage(s1, "Article — Perplexity sonar-pro + web search", "active")
                    status.update(label=f"✍️ [{bidx+1}/{total}] Researching and writing article...")
                    article = generate_article(current["seed"])
                    stage(s1, "Article — Perplexity sonar-pro + web search", "done")

                    stage(s2, "Newsletters & socials — sonar", "active")
                    status.update(label=f"📣 [{bidx+1}/{total}] Writing newsletters and social copy...")
                    dist = generate_distribution(article["title"], article["main_content"])
                    stage(s2, "Newsletters & socials — sonar", "done")

                    stage(s3, "SEO title, description & tags — sonar", "active")
                    status.update(label=f"🔍 [{bidx+1}/{total}] Generating SEO fields...")
                    seo = generate_seo(article["title"], article["main_content"])
                    stage(s3, "SEO title, description & tags — sonar", "done")

                    # Save result
                    st.session_state.batch_results.append({
                        "title":        article["title"],
                        "main_content": article["main_content"],
                        "dist":         dist,
                        "seo":          seo,
                    })

                    # Advance batch or mark done
                    st.session_state.batch_index = bidx + 1
                    if st.session_state.batch_index >= total:
                        # Show last result
                        st.session_state.active_title   = article["title"]
                        st.session_state.active_content = article["main_content"]
                        st.session_state.dist_data      = dist
                        st.session_state.seo_data       = seo
                        st.session_state.generation_ready = True
                        st.session_state.current_batch    = []
                        status.update(
                            label=f"✅ All {total} article{'s' if total>1 else ''} ready!",
                            state="complete", expanded=False
                        )
                    else:
                        status.update(
                            label=f"✅ Article {bidx+1} done — starting {bidx+2}...",
                            state="complete", expanded=False
                        )
                        st.rerun()

                except Exception as err:
                    status.update(label=f"❌ Error: {err}", state="error")
                    st.error(str(err))
                    st.session_state.current_batch = []

        # Show batch results selector (when multiple articles done)
        results = st.session_state.get("batch_results", [])
        if len(results) > 1:
            st.markdown("---")
            st.markdown(f"**{len(results)} articles generated — browse below:**")
            result_titles = [f"{i+1}. {r['title'][:60]}..." for i, r in enumerate(results)]
            chosen = st.selectbox("Select article to preview", result_titles, key="result_picker")
            chosen_idx = result_titles.index(chosen)
            r = results[chosen_idx]
            st.session_state.active_title   = r["title"]
            st.session_state.active_content = r["main_content"]
            st.session_state.dist_data      = r["dist"]
            st.session_state.seo_data       = r["seo"]
            st.session_state.generation_ready = True

        # Show results
        if st.session_state.generation_ready and st.session_state.generation_source == "news_discovery":
            render_results_tabs("nd")


# ════════════════════════════════════════════════════════════════
# TAB 2 — MANUAL SEED
# ════════════════════════════════════════════════════════════════

with main_tab_manual:
    col_left_m, col_right_m = st.columns([1, 1.4], gap="large")

    with col_left_m:
        st.markdown("#### 📡 News seed")
        seed = st.text_area(
            label="seed",
            height=180,
            placeholder="Paste any news or topic seed here...",
            label_visibility="collapsed"
        )

        run_manual = st.button(
            "🚀 Run Production Factory Engine",
            type="primary", use_container_width=True,
            disabled=not seed.strip(),
            key="run_manual"
        )

        st.markdown("---")
        st.markdown("#### ⚙️ Pipeline stages")
        ms1 = st.empty()
        ms2 = st.empty()
        ms3 = st.empty()

        def mstage(slot, label, state="pending"):
            icons = {"pending":"🔘","active":"🔵","done":"✅","error":"❌"}
            slot.markdown(f"{icons.get(state,'🔘')} **{label}**")

        mstage(ms1, "Article — Perplexity sonar-pro + web search")
        mstage(ms2, "Newsletters & socials — sonar")
        mstage(ms3, "SEO title, description & tags — sonar")

    if run_manual and seed.strip():
        st.session_state.generation_source = "manual"
        st.session_state.generation_ready  = False
        st.session_state.push_success      = False

        with col_right_m:
            with st.status("⚙️ Building asset cluster...", expanded=True) as status:
                try:
                    mstage(ms1, "Article — Perplexity sonar-pro + web search", "active")
                    status.update(label="✍️ Researching and writing article...")
                    article = generate_article(seed)
                    st.session_state.active_title   = article["title"]
                    st.session_state.active_content = article["main_content"]
                    mstage(ms1, "Article — Perplexity sonar-pro + web search", "done")

                    mstage(ms2, "Newsletters & socials — sonar", "active")
                    status.update(label="📣 Writing newsletters and social copy...")
                    dist = generate_distribution(article["title"], article["main_content"])
                    st.session_state.dist_data = dist
                    mstage(ms2, "Newsletters & socials — sonar", "done")

                    mstage(ms3, "SEO title, description & tags — sonar", "active")
                    status.update(label="🔍 Generating SEO fields...")
                    seo = generate_seo(article["title"], article["main_content"])
                    st.session_state.seo_data = seo
                    mstage(ms3, "SEO title, description & tags — sonar", "done")

                    st.session_state.generation_ready = True
                    status.update(label="✅ All assets ready!", state="complete", expanded=False)

                except Exception as err:
                    status.update(label=f"❌ Error: {err}", state="error")
                    st.error(str(err))

    if st.session_state.generation_ready and st.session_state.generation_source == "manual":
        with col_right_m:
            render_results_tabs("manual")
