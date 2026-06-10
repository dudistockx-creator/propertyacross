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
- CRITICAL FORMATTING: Do NOT use asterisks (*) for bold. Do NOT use dashes (-) as bullet points. Plain text and → arrows only.
- NO generic buzzwords. NO "game-changer". NO "exciting opportunity".
FACEBOOK VARIANT:
- Community investor tone, warm and approachable
- Short paragraphs, no bullet points, no asterisks, no dashes
- End with an engaging question to drive comments
- Include relevant hashtags at the bottom
X / TWITTER: Punchy hook-first post under 280 chars with 1-2 hashtags. No asterisks. No dashes.
INSTAGRAM VARIANT:
- Hook first line that stops the scroll
- 5-8 short punchy lines each on its own line
- Visual and aspirational tone — paint a picture of the investment opportunity
- End with: "Link in bio for the full analysis."
- Include 10-15 relevant hashtags on a separate line at the bottom
- No asterisks. No dashes. Emojis sparingly for visual breaks only.
PINTEREST VARIANT:
- 2-3 sentence SEO-optimised description
- Include the key yield figure, location, and investment type
- End with a call to action
- No asterisks. No dashes.
INSTAGRAM IMAGE PROMPT:
- Write a detailed cinematic 4:5 vertical Instagram cover image generation prompt
- Magazine-style real estate editorial composition
- Layered cityscape or property panels, dramatic contrast
- Bold dark gradient bar across lower third
- Large bold headline typography in foreground, key words in blue and white
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
- seo_title: Maximum 60 characters. Write like a top Ahrefs/Backlinko headline — front-load the most valuable keyword or number, make it impossible not to click, speak directly to the investor's self-interest. NEVER start with Will, Is, Are, Can, Should, What, How, Does. NEVER use: Guide, Overview, Everything You Need, Ultimate, Comprehensive. USE: specific numbers/yields, city+asset type, power words like Hits, Beats, Reveals, Unlocks, Surges, Outpaces, Closes, Targets. Examples of strong style: "Dubai Offices Hit 9.1% — 3x the Residential Yield", "Lisbon Fractional Closes at 7.2% Before Q3", "Bangkok Condos Outpace London BTL for First Time".
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
FEATURED_IMAGE_PROMPT = """
You are a creative director for PropertyAcross.com producing AI image generation prompts.
Given the article title and key content details below, write ONE featured image prompt.
The prompt must describe a cinematic vertical editorial thumbnail in the style of a high-end real estate feature.
Use a polished magazine-style composition with layered cityscape panels, dramatic contrast, and strong urban energy.
Add a bold dark gradient bar across the lower portion of the image for text readability.
In the foreground, place large, powerful headline text — bold, clean, modern, and highly legible,
with the most important words emphasized in blue and white.
Photorealistic, high-resolution, editorial magazine style, crisp architecture details,
premium investment media look. Format: 16:9.
The prompt must be specific to the article:
- Name the exact city, country, and building/asset type from the article
- Reference the architectural style, skyline, or landmark if relevant
- Include the investment angle visually (e.g. yield percentage as overlay text, currency symbol, investor silhouette)
- Specify time of day, lighting mood, and atmosphere that fits the market story
- Keep it under 120 words — tight, vivid, directive
Output ONLY a valid JSON object:
{
  "featured_image_prompt": "Full detailed image generation prompt here"
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
            "active_content", "dist_data", "seo_data",
            "instagram_copy", "instagram_image_prompt",
            "featured_image_prompt"]:
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
    text = re.sub(r'[*]+', '', text)
    text = re.sub(r'(?m)^\s*[-]\s+', '', text)
    return text.strip()
def call_perplexity(messages: list, model: str = "sonar-pro", json_format: bool = True) -> str:
    if not PERPLEXITY_API_KEY:
        raise Exception("PERPLEXITY_API_KEY is missing from secrets.")
    enforced_messages = messages.copy()
    if json_format:
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
            "You are a senior headline writer for a premium real estate investment publication. "
            "Given the news seed, return ONLY a JSON object: {\"title\": \"...\"}. "
            "\n\nHEADLINE RULES: "
            "\n- Maximum 70 characters "
            "\n- Lead with the most surprising number, location, or contrarian angle "
            "\n- Use varied structures: statements, how-to, comparisons, data-led, contrarian, insider angles "
            "\n- NEVER start with Will, Is, Are, Can, Should, Does, Do, Has, Have, or What "
            "\n- NEVER use: game-changer, booming, thriving, exciting, incredible, comprehensive guide "
            "\n- Include city/country + asset type naturally "
            "\n- Include a specific number, yield, price, or % where possible "
            "\n\nSTRONG PATTERNS — rotate through these, never repeat the same structure twice: "
            "\n- Data statement: Dubai Marina Offices Hit 9.1% Yield — Beating Residential by 3x "
            "\n- Contrarian: Why Bangkok Condos Outperform London Buy-to-Let in 2026 "
            "\n- Insider angle: The Georgian CBI Loophole Attracting $2B in European Capital "
            "\n- How-to: How Lisbon Fractional Investors Lock In 7% Before Q3 Closings "
            "\n- Comparison: Athens vs Nicosia — Where 250K Buys the Better Residency Yield "
            "\n- Trend reveal: Vietnam Industrial REITs Just Outpaced Singapore for the First Time "
            "\n- Urgency/stakes: Morocco CBI Window Closes in 90 Days — The Investment Case "
            "\nABSOLUTE RULE: Return only the JSON object. Nothing else."
        )},
        {"role": "user", "content": f"News seed:\n{raw_input}"}
    ]
    title_text = call_perplexity(title_messages, model="sonar", json_format=True)
    title_result = safe_parse_json(title_text)
    title = strip_citations(title_result.get("title", "Untitled"))
    # Step 2: Generate article body as plain HTML (no JSON wrapper, uses full token budget)
    body_messages = [
        {"role": "system", "content": (
            "You are the Lead SEO Architect for PropertyAcross.com, writing for serious real estate investors. "
            "Use live web search to enrich the article with current statistics, yield figures, and price data. "
            "Follow these professional SEO content rules used by Ahrefs, HubSpot, and top-ranking investment publications:\n\n"
            "STRUCTURE:\n"
            "1. Opening intro paragraph (50-80 words): Answer the core investor question immediately in 2-3 sentences. "
            "State the key data point or finding upfront. Use the inverted pyramid — most important fact first.\n"
            "2. Key Takeaways box: Add a <ul> with 3-4 bullet points summarising the most important data points investors need to know. "
            "Label it with <strong>Key Takeaways</strong> before the list.\n"
            "3. Question-based H2/H3 subheadings: Each heading must be a specific investor question "
            "(e.g. 'What rental yields can investors realistically expect in 2026?').\n"
            "4. Under each H2/H3: Write exactly 2-3 paragraphs. Each paragraph must be 80-120 words maximum. "
            "Each sentence must be 15-20 words maximum. Active voice only. No passive constructions.\n"
            "5. Every factual claim must name its source inline using natural attribution "
            "(e.g. 'according to Knight Frank', 'JLL data shows', 'the Ministry of Migration confirmed'). "
            "No numbered citation markers like [1] or [2].\n"
            "6. Add transition sentences between sections to maintain reading flow.\n"
            "7. FAQ block at the end: 5-7 questions. Each answer must be 40-60 words — tight, direct, snippet-optimised. "
            "Write FAQ answers as if they will appear as Google featured snippets.\n"
            "8. Closing CTA paragraph (40-60 words): Summarise the investment case and direct readers to explore more on PropertyAcross.com.\n\n"
            "TONE & LANGUAGE:\n"
            "- Write like a senior analyst at a premium investment bank, not a real estate agent.\n"
            "- Use active voice: 'Investors earn 6.2%' not 'A yield of 6.2% is earned by investors'.\n"
            "- No filler phrases: never use 'it is worth noting', 'it is important to', 'in conclusion', 'in today\'s market'.\n"
            "- No fluff adjectives: never use 'booming', 'thriving', 'exciting', 'incredible', 'remarkable'.\n"
            "- Replace vague claims with numbers: never say 'strong yields' — say '6.4% gross yield'.\n"
            "- Vary sentence length: mix short punchy sentences (8-10 words) with longer analytical ones (18-22 words).\n\n"
            "FORMATTING RULES:\n"
            "- Use only these HTML tags: h2, h3, p, strong, ul, li. Do NOT use h1.\n"
            "- No inline styles. No div tags. No tables.\n"
            "- Output ONLY the raw HTML body. No JSON. No markdown fences. No preamble. No citation markers like [1][2]."
        )},
        {"role": "user", "content": f"Article title: {title}\n\nNews seed: {raw_input}"}
    ]
    body_text = call_perplexity(body_messages, model="sonar-pro", json_format=False)
    
    # Strip markdown code fences if present
    body_text = re.sub(r'^```html\s*|^```\s*', '', body_text, flags=re.IGNORECASE)
    body_text = re.sub(r'\s*```$', '', body_text)
    
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
def generate_featured_image_prompt(title: str, content: str) -> str:
    messages = [
        {"role": "system", "content": FEATURED_IMAGE_PROMPT},
        {"role": "user",   "content": f"Article title: {title}\n\nArticle content (first 2000 chars):\n{content[:2000]}"}
    ]
    text = call_perplexity(messages, model="sonar")
    result = safe_parse_json(text)
    if isinstance(result, list):
        result = result[0]
    return strip_citations(result.get("featured_image_prompt", ""))
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
            "pinterest_copy":       dist.get("pinterest_copy", ""),
            "_yoast_wpseo_title":   seo.get("seo_title", ""),
            "_yoast_wpseo_metadesc":seo.get("seo_description", ""),
            "rank_math_focus_keyword": seo.get("seo_tags", ""),
            "_yoast_wpseo_focuskw": seo.get("seo_tags", "").split(",")[0].strip() if seo.get("seo_tags") else "",
            "featured_image_prompt": st.session_state.get("featured_image_prompt", ""),
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
    s4 = st.empty()
    def stage(slot, label, state="pending"):
        icon = {"pending": "🔘", "active": "🔵", "done": "✅", "error": "❌"}
        slot.markdown(f"{icon.get(state, '🔘')} **{label}**")
    stage(s1, "Article — Perplexity sonar-pro + web search")
    stage(s2, "Newsletters & socials — Perplexity sonar")
    stage(s3, "SEO title, description & tags — Perplexity sonar")
    stage(s4, "Featured image prompt — Perplexity sonar")
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
                stage(s4, "Featured image prompt — Perplexity sonar", "active")
                status.update(label="🖼️ Stage 4: Generating featured image prompt...")
                featured_img = generate_featured_image_prompt(
                    st.session_state.active_title,
                    st.session_state.active_content
                )
                st.session_state.featured_image_prompt = featured_img
                stage(s4, "Featured image prompt — Perplexity sonar", "done")
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
        tab_art, tab_nl, tab_soc, tab_seo, tab_img = st.tabs([
            "📝 Article", "📧 Newsletters", "💼 Socials", "🔍 SEO", "🖼️ Featured Image"
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
        with tab_img:
            st.markdown("**🖼️ Featured Image Prompt (16:9)**")
            st.caption("Copy this into Midjourney, DALL·E, Firefly, or any image generator.")
            img_prompt = st.session_state.get("featured_image_prompt", "")
            st.code(img_prompt, language="text")
            if img_prompt:
                char_count_img = len(img_prompt)
                st.markdown(f"*{char_count_img} characters*")
                # One-click copy helper
                st.text_area(
                    "✏️ Edit before copying",
                    value=img_prompt,
                    height=160,
                    key="img_prompt_edit",
                    label_visibility="visible"
                )