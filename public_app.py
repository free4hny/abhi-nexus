"""
public_app.py
─────────────────────────────────────────────
Public read-only Streamlit page.
No login required. No admin controls.
Shows top 20 articles with scores and summaries.
TTS narration works for anyone.

Run on a separate port:
  streamlit run public_app.py --server.port 8502
"""

import streamlit as st
import streamlit.components.v1 as components
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Abhi-Nexus · Public",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────
st.markdown("""
<style>
.stApp { background-color: #0a0800; color: #f5e6c8; }

[data-testid="stSidebar"] {
    background-color: #110e00;
    border-right: 1px solid #8B6914;
}

h1, h2, h3, h4, p, span, label, div {
    color: #f5e6c8;
}

hr { border-color: #8B6914 !important; opacity: 0.4; }

.stButton > button {
    background-color: #8B6914;
    color: #0a0800;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}
.stButton > button:hover {
    background-color: #FFD700;
    color: #0a0800;
}

[data-baseweb="select"] * {
    background-color: #1a1400 !important;
    color: #FFD700 !important;
}
[data-baseweb="menu"] {
    background-color: #1a1400 !important;
    border: 1px solid #8B6914 !important;
}
[data-baseweb="option"]:hover {
    background-color: #8B6914 !important;
    color: #0a0800 !important;
}

.stRadio label { color: #c9a84c !important; }

.section-header {
    font-size: 13px;
    color: #8B6914;
    letter-spacing: 3px;
    text-transform: uppercase;
    font-family: monospace;
    margin: 24px 0 16px;
    border-bottom: 1px solid #8B6914;
    padding-bottom: 8px;
}
.stat-card {
    background: #1a1400;
    border: 1px solid #8B6914;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
}
.stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #FFD700;
    font-family: monospace;
}
.stat-label {
    font-size: 11px;
    color: #8B6914;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: monospace;
}
.hot-card {
    background: #1a1400;
    border: 1px solid #8B6914;
    border-top: 3px solid #FFD700;
    border-radius: 10px;
    padding: 16px;
    height: 100%;
}
.public-badge {
    display: inline-block;
    background: rgba(139,105,20,0.2);
    border: 1px solid #8B6914;
    color: #8B6914;
    font-size: 10px;
    padding: 3px 10px;
    border-radius: 4px;
    font-family: monospace;
    letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)


# ── Data loading ───────────────────────────────

@st.cache_data(ttl=300)
def load_articles():
    """
    Load public articles — no auth needed.
    Cached for 5 minutes so rapid page loads
    do not hammer the API.
    """
    try:
        r = requests.get(
            f"{API_URL}/public/articles",
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
        return {"articles": [], "updated_at": None}
    except Exception:
        return {"articles": [], "updated_at": None}


# ── Score color ────────────────────────────────

def score_html(score):
    color = (
        "#4ade80" if score >= 70 else
        "#FFD700" if score >= 40 else
        "#f87171"
    )
    return (
        f'<span style="color:{color};font-weight:700;'
        f'font-family:monospace;">{score}/100</span>'
    )


# ── TTS buttons ────────────────────────────────

def narration_buttons(article: dict):
    """
    Public TTS — calls /public/tts (no auth needed).
    Uses browser Web Speech API as fallback if
    no API key available.
    """
    en_text    = (article.get("ai_summary") or
                  article.get("summary") or
                  article.get("title") or "")[:800]
    hi_text    = (article.get("hindi_summary") or
                  en_text)[:800]
    en_text_js = en_text.replace('"', '\\"').replace('\n', ' ')
    hi_text_js = hi_text.replace('"', '\\"').replace('\n', ' ')
    api_url    = API_URL

    html = f"""
    <div style="display:flex;gap:8px;margin-top:8px;
                align-items:center;">
      <button onclick="playTTS('{api_url}',
                               '{en_text_js}','en',this)"
        id="btn-en"
        style="background:rgba(139,105,20,0.15);
               border:1px solid #8B6914;color:#FFD700;
               padding:5px 14px;border-radius:6px;
               font-size:11px;font-family:monospace;
               cursor:pointer;letter-spacing:1px;">
        🔊 EN
      </button>
      <button onclick="playTTS('{api_url}',
                               '{hi_text_js}','hi',this)"
        id="btn-hi"
        style="background:rgba(139,105,20,0.15);
               border:1px solid #8B6914;color:#FFD700;
               padding:5px 14px;border-radius:6px;
               font-size:11px;font-family:monospace;
               cursor:pointer;letter-spacing:1px;">
        🎙 हिन्दी
      </button>
      <button onclick="stopAudio()" id="btn-stop"
        style="display:none;
               background:rgba(220,38,38,0.15);
               border:1px solid #dc2626;color:#f87171;
               padding:5px 14px;border-radius:6px;
               font-size:11px;font-family:monospace;
               cursor:pointer;letter-spacing:1px;">
        ■ STOP
      </button>
      <span id="tts-status"
        style="font-size:11px;color:#8B6914;
               font-family:monospace;"></span>
    </div>
    <script>
    var currentAudio = null;
    function stopAudio() {{
      if (currentAudio) {{
        currentAudio.pause();
        currentAudio.src = '';
        currentAudio = null;
      }}
      var s = document.getElementById('btn-stop');
      var t = document.getElementById('tts-status');
      var e = document.getElementById('btn-en');
      var h = document.getElementById('btn-hi');
      if (s) s.style.display = 'none';
      if (t) t.innerText = '';
      if (e) e.disabled = false;
      if (h) h.disabled = false;
    }}
    async function playTTS(apiUrl, text, lang, btn) {{
      stopAudio();
      var s    = document.getElementById('btn-stop');
      var t    = document.getElementById('tts-status');
      var e    = document.getElementById('btn-en');
      var h    = document.getElementById('btn-hi');
      var orig = btn.innerText;
      btn.innerText = '⏳';
      btn.disabled  = true;
      if (lang==='en' && h) h.disabled = true;
      if (lang==='hi' && e) e.disabled = true;
      if (t) t.innerText = 'generating...';
      try {{
        var res = await fetch(apiUrl+'/public/tts', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{text:text, lang:lang}}),
        }});
        if (!res.ok) {{
          // fallback to browser speech
          browserSpeak(text, lang);
          btn.innerText = orig; btn.disabled = false;
          if (lang==='en' && h) h.disabled = false;
          if (lang==='hi' && e) e.disabled = false;
          if (t) t.innerText = '';
          return;
        }}
        var blob  = await res.blob();
        var url   = URL.createObjectURL(blob);
        var audio = new Audio(url);
        currentAudio = audio;
        audio.oncanplay = function() {{
          if (t) t.innerText = '▶ playing';
          btn.innerText = orig;
          if (s) s.style.display = 'inline-block';
        }};
        audio.onended = function() {{
          URL.revokeObjectURL(url);
          currentAudio = null;
          if (s) s.style.display = 'none';
          if (t) t.innerText = '';
          btn.disabled = false;
          if (lang==='en' && h) h.disabled = false;
          if (lang==='hi' && e) e.disabled = false;
        }};
        audio.play();
      }} catch(err) {{
        browserSpeak(text, lang);
        btn.innerText = orig; btn.disabled = false;
        if (lang==='en' && h) h.disabled = false;
        if (lang==='hi' && e) e.disabled = false;
        if (t) t.innerText = '';
      }}
    }}
    function browserSpeak(text, lang) {{
      var u = new SpeechSynthesisUtterance(text);
      u.lang = lang === 'hi' ? 'hi-IN' : 'en-US';
      u.rate = 0.9;
      speechSynthesis.speak(u);
    }}
    </script>
    """
    components.html(html, height=70)


# ── Article card ───────────────────────────────

def article_card(a: dict):
    score   = a.get("score", 0)
    tags    = a.get("tags", [])
    summary = (a.get("ai_summary") or
               a.get("summary") or "")[:280]

    with st.container(border=True):
        col_title, col_score = st.columns([5, 1])

        with col_title:
            st.markdown(
                f'<span style="color:#8B6914;font-size:12px;'
                f'font-family:monospace;">#{a.get("rank","?")}'
                f'</span>'
                f' **[{a.get("title","")}]({a.get("url","#")})**',
                unsafe_allow_html=True
            )

        with col_score:
            st.markdown(score_html(score),
                        unsafe_allow_html=True)

        st.caption(
            f"{a.get('source','')} · "
            f"{a.get('category','')} · "
            f"Rank #{a.get('rank','?')}"
        )

        if summary:
            st.markdown(
                f'<p style="color:#c9a84c;font-size:13px;'
                f'line-height:1.6;margin:4px 0;">{summary}</p>',
                unsafe_allow_html=True
            )

        if tags:
            tags_html = "".join(
                f'<span style="display:inline-block;'
                f'background:rgba(139,105,20,0.2);'
                f'border:1px solid #8B6914;color:#c9a84c;'
                f'font-size:10px;padding:2px 8px;'
                f'border-radius:4px;margin-right:4px;'
                f'font-family:monospace;">{t}</span>'
                for t in tags
            )
            st.markdown(tags_html, unsafe_allow_html=True)

        narration_buttons(a)


# ── Hot section ────────────────────────────────

def hot_section(articles: list):
    hot = [a for a in articles if a.get("is_hot")][:5]
    if not hot:
        return
    st.markdown(
        '<div class="section-header">🔥 top stories</div>',
        unsafe_allow_html=True
    )
    cols = st.columns(len(hot))
    for col, a in zip(cols, hot):
        with col:
            title = a.get("title", "")
            st.markdown(f"""
            <div class="hot-card">
              <div style="font-size:11px;color:#8B6914;
                          font-family:monospace;
                          margin-bottom:6px;">
                #{a.get('rank')} · {a.get('score')}/100
              </div>
              <div style="font-size:13px;font-weight:600;
                          line-height:1.4;margin-bottom:8px;">
                <a href="{a.get('url','#')}" target="_blank"
                   style="color:#FFD700;text-decoration:none;">
                  {title[:80]}{"..." if len(title)>80 else ""}
                </a>
              </div>
              <div style="font-size:11px;color:#8B6914;
                          font-family:monospace;">
                {a.get('source','')}
              </div>
            </div>
            """, unsafe_allow_html=True)


# ── Main page ──────────────────────────────────

def main():
    # header
    st.markdown("""
    <div style="display:flex;align-items:center;
                justify-content:space-between;
                margin-bottom:8px;">
      <div>
        <span style="font-size:28px;font-weight:700;
                     color:#FFD700;letter-spacing:2px;
                     font-family:monospace;">
          🔷 ABHI-NEXUS
        </span>
        <span style="font-size:12px;color:#8B6914;
                     font-family:monospace;margin-left:16px;">
          PERSONAL TECH INTELLIGENCE
        </span>
      </div>
      <span class="public-badge">PUBLIC · READ ONLY</span>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # load data
    with st.spinner("Loading..."):
        data     = load_articles()
        articles = data.get("articles", [])

    if not articles:
        st.warning(
            "No articles available yet. "
            "Check back soon — content updates automatically."
        )
        return

    # stats
    scores = [a.get("score", 0) for a in articles]
    avg    = sum(scores) // max(len(scores), 1)
    hot_c  = sum(1 for a in articles if a.get("is_hot"))
    cats   = len(set(a.get("category") for a in articles))
    upd    = data.get("updated_at", "")
    upd    = upd[11:19] + " UTC" if upd else "—"

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label in [
        (c1, len(articles), "ARTICLES"),
        (c2, hot_c,         "HOT STORIES"),
        (c3, f"{avg}/100",  "AVG SCORE"),
        (c4, upd,           "LAST UPDATED"),
    ]:
        with col:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-value">{val}</div>
              <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # category filter
    cats_list = ["All"] + sorted(set(
        a.get("category", "General") for a in articles
    ))
    selected = st.radio(
        "Filter",
        cats_list,
        horizontal=True,
        label_visibility="collapsed",
    )

    st.divider()

    # filter articles
    filtered = (
        articles if selected == "All"
        else [a for a in articles
              if a.get("category") == selected]
    )

    # hot section
    if selected == "All":
        hot_section(filtered)
        st.markdown("<br>", unsafe_allow_html=True)

    # articles
    st.markdown(
        f'<div class="section-header">'
        f'📰 {selected.lower()} articles · '
        f'{len(filtered)} ranked by importance</div>',
        unsafe_allow_html=True
    )

    display = (
        [a for a in filtered if not a.get("is_hot")]
        if selected == "All" else filtered
    )

    for a in display:
        article_card(a)

    # footer
    st.divider()
    st.markdown("""
    <div style="text-align:center;padding:16px 0;">
      <span style="font-size:11px;color:#8B6914;
                   font-family:monospace;">
        POWERED BY ABHI-NEXUS MULTI-AGENT SYSTEM ·
        UPDATES EVERY 2 HOURS
      </span>
    </div>
    """, unsafe_allow_html=True)


main()