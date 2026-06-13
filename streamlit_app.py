"""
streamlit_app.py
─────────────────────────────────────────────
Phase 5 + 6 — Streamlit UI with Admin Panel

Dark gold theme. Two tabs for admin:
  📰 NEWS FEED   — articles, hot stories, TTS
  ⚙ ADMIN PANEL — scheduler, email settings
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Abhi-Nexus",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────
st.markdown("""
<style>
/* ── Selectbox ── */
.stSelectbox > div > div {
    background-color: #1a1400 !important;
    border: 1px solid #8B6914 !important;
    color: #FFD700 !important;
    border-radius: 8px !important;
}
.stSelectbox > div > div > div {
    color: #FFD700 !important;
}
/* dropdown menu items */
[data-baseweb="select"] * {
    background-color: #1a1400 !important;
    color: #FFD700 !important;
}
[data-baseweb="menu"] {
    background-color: #1a1400 !important;
    border: 1px solid #8B6914 !important;
}
[data-baseweb="option"] {
    background-color: #1a1400 !important;
    color: #FFD700 !important;
}
[data-baseweb="option"]:hover {
    background-color: #8B6914 !important;
    color: #0a0800 !important;
}
/* time input */
[data-testid="stTimeInput"] input {
    background-color: #1a1400 !important;
    border: 1px solid #8B6914 !important;
    color: #FFD700 !important;
    border-radius: 8px !important;
}
/* text area */
.stTextArea textarea {
    background-color: #1a1400 !important;
    border: 1px solid #8B6914 !important;
    color: #FFD700 !important;
    border-radius: 8px !important;
}
/* toggle label */
.stToggle p {
    color: #c9a84c !important;
}
/* tab text */
.stTabs [data-baseweb="tab"] {
    color: #c9a84c !important;
    font-family: monospace !important;
    letter-spacing: 1px !important;
}
.stTabs [aria-selected="true"] {
    color: #FFD700 !important;
    border-bottom-color: #FFD700 !important;
}
/* caption text */
.stCaptionContainer p {
    color: #8B6914 !important;
    font-family: monospace !important;
}
/* warning/success/error messages */
.stAlert {
    background-color: #1a1400 !important;
    border: 1px solid #8B6914 !important;
    color: #FFD700 !important;
}
/* spinner text */
.stSpinner p {
    color: #c9a84c !important;
}
/* radio button text */
.stRadio p {
    color: #c9a84c !important;
}
/* general text override */
p, span, div, label {
    color: #c9a84c;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────
def init_session_state():
    defaults = {
        "token":    None,
        "username": None,
        "role":     None,
        "category": "All",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()


# ── API helpers ────────────────────────────────

def api_login(username, password):
    try:
        r = requests.post(
            f"{API_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

@st.cache_data(ttl=300)
def get_articles(category=None):
    try:
        params = {}
        if category and category != "All":
            params["category"] = category
        r = requests.get(
            f"{API_URL}/articles",
            headers=headers(),
            params=params,
            timeout=10,
        )
        return r.json().get("articles", []) \
               if r.status_code == 200 else []
    except Exception:
        return []

@st.cache_data(ttl=300)
def get_categories():
    try:
        r = requests.get(
            f"{API_URL}/articles/categories",
            headers=headers(),
            timeout=10,
        )
        return ["All"] + r.json().get("categories", []) \
               if r.status_code == 200 else ["All"]
    except Exception:
        return ["All"]

def get_status():
    try:
        r = requests.get(f"{API_URL}/status",
                         headers=headers(), timeout=5)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}

def run_pipeline():
    try:
        r = requests.post(f"{API_URL}/pipeline/run",
                          headers=headers(), timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def api_get_settings():
    try:
        r = requests.get(f"{API_URL}/settings",
                         headers=headers(), timeout=5)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}

def api_save_settings(body: dict) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{API_URL}/settings",
            headers=headers(),
            json=body,
            timeout=5,
        )
        if r.status_code == 200:
            return True, "Settings saved"
        return False, r.json().get("detail", "Error")
    except Exception as e:
        return False, str(e)

def api_send_test_email(recipients: list) -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{API_URL}/email/test",
            headers=headers(),
            json={"recipients": recipients},
            timeout=30,
        )
        if r.status_code == 200:
            return True, r.json().get("message", "Sent")
        return False, r.json().get("detail", "Failed")
    except Exception as e:
        return False, str(e)

def api_scheduler_status():
    try:
        r = requests.get(f"{API_URL}/scheduler/status",
                         headers=headers(), timeout=5)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


# ── Score color ────────────────────────────────

def score_html(score):
    cls = ("score-high" if score >= 70 else
           "score-mid"  if score >= 40 else
           "score-low")
    return f'<span class="{cls}">{score}/100</span>'


# ── Narration buttons ──────────────────────────

def narration_buttons(article: dict):
    """
    Inject HTML+JS TTS buttons into the page.
    Calls FastAPI /tts from the browser directly.
    Uses JWT token stored in session state.
    """
    token      = st.session_state.token
    en_text    = (article.get("ai_summary") or
                  article.get("summary") or
                  article.get("title") or "")[:800]
    hi_text    = (article.get("hindi_summary") or
                  en_text)[:800]
    en_text_js = en_text.replace('"', '\\"').replace('\n', ' ')
    hi_text_js = hi_text.replace('"', '\\"').replace('\n', ' ')

    html = f"""
    <div style="display:flex;gap:8px;margin-top:8px;
                align-items:center;">
      <button onclick="playTTS('{API_URL}','{token}',
                               '{en_text_js}','en',this)"
        id="btn-en"
        style="background:rgba(139,105,20,0.15);
               border:1px solid #8B6914;color:#FFD700;
               padding:5px 14px;border-radius:6px;
               font-size:11px;font-family:monospace;
               cursor:pointer;letter-spacing:1px;">
        🔊 EN
      </button>
      <button onclick="playTTS('{API_URL}','{token}',
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
    <audio id="tts-player"></audio>
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
    async function playTTS(apiUrl, token, text, lang, btn) {{
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
      if (s) s.style.display = 'none';
      try {{
        var res = await fetch(apiUrl+'/tts', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
            'Authorization': 'Bearer '+token,
          }},
          body: JSON.stringify({{text:text, lang:lang}}),
        }});
        if (!res.ok) {{
          if (t) t.innerText = 'error '+res.status;
          btn.innerText = orig; btn.disabled = false;
          if (lang==='en' && h) h.disabled = false;
          if (lang==='hi' && e) e.disabled = false;
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
        audio.onerror = function() {{
          if (t) t.innerText = 'playback error';
          btn.innerText = orig; btn.disabled = false;
          if (lang==='en' && h) h.disabled = false;
          if (lang==='hi' && e) e.disabled = false;
          if (s) s.style.display = 'none';
          currentAudio = null;
        }};
        audio.play();
      }} catch(err) {{
        if (t) t.innerText = 'connection error';
        btn.innerText = orig; btn.disabled = false;
        if (lang==='en' && h) h.disabled = false;
        if (lang==='hi' && e) e.disabled = false;
        if (s) s.style.display = 'none';
      }}
    }}
    </script>
    """
    components.html(html, height=70)


# ── Article card ───────────────────────────────

def article_card(a: dict):
    score   = a.get("score", 0)
    is_hot  = a.get("is_hot", False)
    tags    = a.get("tags", [])
    summary = (a.get("ai_summary") or
               a.get("summary") or "")[:280]

    with st.container(border=True):
        # top row — title and score
        col_title, col_score = st.columns([5, 1])

        with col_title:
            if is_hot:
                st.markdown(
                    '<span style="background:#8B6914;'
                    'color:#0a0800;font-size:10px;'
                    'font-weight:700;padding:2px 8px;'
                    'border-radius:4px;font-family:monospace;'
                    'margin-right:8px;">HOT</span>',
                    unsafe_allow_html=True
                )
            st.markdown(
                f'<span style="color:#8B6914;font-size:12px;'
                f'font-family:monospace;">#{a.get("rank","?")}</span>'
                f' **[{a.get("title","")}]({a.get("url","#")})**',
                unsafe_allow_html=True
            )

        with col_score:
            if score >= 70:
                st.markdown(
                    f'<span style="color:#4ade80;font-weight:700;'
                    f'font-family:monospace;">{score}/100</span>',
                    unsafe_allow_html=True
                )
            elif score >= 40:
                st.markdown(
                    f'<span style="color:#FFD700;font-weight:700;'
                    f'font-family:monospace;">{score}/100</span>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<span style="color:#f87171;font-weight:700;'
                    f'font-family:monospace;">{score}/100</span>',
                    unsafe_allow_html=True
                )

        # metadata
        st.caption(
            f"{a.get('source','')} · "
            f"{a.get('category','')} · "
            f"Rank #{a.get('rank','?')}"
        )

        # summary
        if summary:
            st.markdown(
                f'<p style="color:#c9a84c;font-size:13px;'
                f'line-height:1.6;margin:4px 0;">{summary}</p>',
                unsafe_allow_html=True
            )

        # tags
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

        # TTS buttons
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
              <div class="hot-card-rank">
                #{a.get('rank')} · {a.get('score')}/100
              </div>
              <div class="hot-card-title">
                <a href="{a.get('url','#')}" target="_blank"
                   style="color:#FFD700;text-decoration:none;">
                  {title[:80]}{"..." if len(title)>80 else ""}
                </a>
              </div>
              <div class="hot-card-source">
                {a.get('source','')}
              </div>
            </div>
            """, unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:16px 0 8px;">
          <div style="font-size:32px;">🔷</div>
          <div style="font-size:18px;font-weight:700;
                      color:#FFD700;letter-spacing:2px;
                      font-family:monospace;">ABHI-NEXUS</div>
          <div style="font-size:11px;color:#8B6914;
                      letter-spacing:1px;font-family:monospace;">
            PERSONAL TECH INTELLIGENCE
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        role_icon = "⭐" if st.session_state.role == "admin" \
                    else "👤"
        st.markdown(f"""
        <div style="font-family:monospace;font-size:12px;
                    color:#8B6914;padding:4px 0;">
          {role_icon} {st.session_state.username.upper()}
          · {st.session_state.role.upper()}
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.markdown(
            '<div style="font-size:11px;color:#8B6914;'
            'letter-spacing:2px;font-family:monospace;'
            'margin-bottom:8px;">FILTER BY CATEGORY</div>',
            unsafe_allow_html=True
        )
        cats     = get_categories()
        selected = st.radio(
            "category", cats,
            index=cats.index(st.session_state.category)
                  if st.session_state.category in cats else 0,
            label_visibility="collapsed",
        )
        if selected != st.session_state.category:
            st.session_state.category = selected
            get_articles.clear()
            st.rerun()

        st.divider()

        st.markdown(
            '<div style="font-size:11px;color:#8B6914;'
            'letter-spacing:2px;font-family:monospace;'
            'margin-bottom:8px;">PIPELINE STATUS</div>',
            unsafe_allow_html=True
        )
        status = get_status()
        s      = status.get("status", "idle")
        dot    = {"done":"🟢","running":"🟡",
                  "error":"🔴","idle":"⚪"}.get(s,"⚪")
        last   = status.get("completed_at", "")
        last   = last[11:19] + " UTC" if last else "—"
        st.markdown(
            f'<div style="font-family:monospace;font-size:12px;'
            f'color:#8B6914;">{dot} {s.upper()}<br>'
            f'ARTICLES: {status.get("articles_count",0)}<br>'
            f'LAST RUN: {last}</div>',
            unsafe_allow_html=True
        )

        if st.session_state.role == "admin":
            st.divider()
            st.markdown(
                '<div style="font-size:11px;color:#8B6914;'
                'letter-spacing:2px;font-family:monospace;'
                'margin-bottom:8px;">QUICK CONTROLS</div>',
                unsafe_allow_html=True
            )
            if st.button("▶ RUN PIPELINE",
                         use_container_width=True):
                with st.spinner("Starting..."):
                    ok = run_pipeline()
                if ok:
                    st.success("Pipeline started!")
                    get_articles.clear()
                else:
                    st.error("Failed to start")

        st.divider()
        if st.button("SIGN OUT", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ── News feed ──────────────────────────────────

def render_news_feed():
    with st.spinner("Loading intelligence..."):
        articles = get_articles(st.session_state.category)

    if not articles:
        st.warning(
            "No articles found. "
            "Run the pipeline from the sidebar."
        )
        return

    scores = [a.get("score", 0) for a in articles]
    avg    = sum(scores) // max(len(scores), 1)
    hot_c  = sum(1 for a in articles if a.get("is_hot"))
    cats   = len(set(a.get("category") for a in articles))

    c1, c2, c3, c4 = st.columns(4)
    for col, val, label in [
        (c1, len(articles), "ARTICLES"),
        (c2, hot_c,         "HOT STORIES"),
        (c3, f"{avg}/100",  "AVG SCORE"),
        (c4, cats,          "CATEGORIES"),
    ]:
        with col:
            st.markdown(f"""
            <div class="stat-card">
              <div class="stat-value">{val}</div>
              <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.category == "All":
        hot_section(articles)
        st.markdown("<br>", unsafe_allow_html=True)

    cat_label = st.session_state.category
    st.markdown(
        f'<div class="section-header">'
        f'📰 {cat_label.lower()} articles · '
        f'{len(articles)} ranked by importance</div>',
        unsafe_allow_html=True
    )

    display = (
        [a for a in articles if not a.get("is_hot")]
        if st.session_state.category == "All"
        else articles
    )
    for a in display:
        article_card(a)


# ── Admin panel ────────────────────────────────

def render_admin_panel():
    cfg = api_get_settings()

    # ── Scheduler settings ─────────────────────
    st.markdown(
        '<div class="admin-section-title">'
        'SCHEDULER SETTINGS</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        scheduler_enabled = st.toggle(
            "Auto-refresh pipeline",
            value=cfg.get("scheduler_enabled", True),
        )
        interval = st.selectbox(
            "Refresh interval",
            options=[30, 60, 120, 240, 480,720, 960],
            index=[30,60,120,240,480,720, 960].index(
                cfg.get("refresh_interval_minutes", 120)
            ),
            format_func=lambda x:
                f"Every {x} min" if x < 60
                else f"Every {x//60} hour(s)",
        )

    with col2:
        email_enabled = st.toggle(
            "Daily email digest",
            value=cfg.get("email_enabled", True),
        )
        try:
            t_val = datetime.strptime(
                cfg.get("email_time", "21:00"), "%H:%M"
            ).time()
        except Exception:
            from datetime import time
            t_val = time(21, 0)

        email_time = st.time_input(
            "Email send time (EST)",
            value=t_val,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Email settings ─────────────────────────
    st.markdown(
        '<div class="admin-section-title">'
        'EMAIL SETTINGS</div>',
        unsafe_allow_html=True
    )

    current_r       = ", ".join(cfg.get("email_recipients", []))
    recipients_input = st.text_area(
        "Recipients (comma separated)",
        value=current_r,
        height=80,
        placeholder="you@gmail.com, friend@gmail.com",
    )

    last_sent = cfg.get("last_email_sent")
    if last_sent:
        st.caption(f"Last email sent: {str(last_sent)[:19]}")

    col_save, col_test = st.columns(2)

    with col_save:
        if st.button("💾 SAVE SETTINGS",
                     use_container_width=True):
            recipients = [
                r.strip()
                for r in recipients_input.split(",")
                if r.strip()
            ]
            body = {
                "scheduler_enabled":        scheduler_enabled,
                "refresh_interval_minutes": interval,
                "email_enabled":            email_enabled,
                "email_time":               email_time.strftime("%H:%M"),
                "email_recipients":         recipients,
            }
            ok, msg = api_save_settings(body)
            if ok:
                st.success(f"✓ {msg} — scheduler updated immediately")
            else:
                st.error(f"✗ {msg}")

    with col_test:
        if st.button("✉ SEND TEST EMAIL",
                     use_container_width=True):
            recipients = [
                r.strip()
                for r in recipients_input.split(",")
                if r.strip()
            ]
            if not recipients:
                st.error("Add at least one recipient first")
            else:
                with st.spinner("Sending..."):
                    ok, msg = api_send_test_email(recipients)
                if ok:
                    st.success(f"✓ {msg}")
                else:
                    st.error(f"✗ {msg}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Scheduled jobs ─────────────────────────
    st.markdown(
        '<div class="admin-section-title">'
        'SCHEDULED JOBS</div>',
        unsafe_allow_html=True
    )

    sched = api_scheduler_status()
    jobs  = sched.get("jobs", [])

    if jobs:
        for job in jobs:
            next_run = str(job.get("next_run", "unknown"))
            if "." in next_run:
                next_run = next_run.split(".")[0]
            st.markdown(f"""
            <div class="job-card">
              <span style="color:#FFD700;">
                {job.get('id','').upper()}
              </span>
              <span style="color:#8B6914;margin-left:12px;">
                next run → {next_run}
              </span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No scheduled jobs found")


# ── Login page ─────────────────────────────────

def render_login():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("""
        <div style="background:#1a1400;
                    border:1px solid #8B6914;
                    border-radius:16px;padding:40px;
                    text-align:center;margin-bottom:24px;">
          <div style="font-size:48px;">🔷</div>
          <div style="font-size:22px;font-weight:700;
                      color:#FFD700;letter-spacing:3px;
                      font-family:monospace;">ABHI-NEXUS</div>
          <div style="font-size:11px;color:#8B6914;
                      letter-spacing:2px;font-family:monospace;
                      margin-top:4px;">
            PERSONAL TECH INTELLIGENCE
          </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login"):
            username  = st.text_input("USERNAME")
            password  = st.text_input("PASSWORD",
                                      type="password")
            submitted = st.form_submit_button(
                "→ ACCESS SYSTEM",
                use_container_width=True,
            )

        if submitted:
            with st.spinner("Authenticating..."):
                result = api_login(username, password)
            if result:
                st.session_state.token    = result["access_token"]
                st.session_state.username = result["username"]
                st.session_state.role     = result["role"]
                st.rerun()
            else:
                st.error("Invalid credentials")


# ── Main dashboard ─────────────────────────────

def render_main():
    render_sidebar()

    st.markdown("""
    <div style="margin-bottom:8px;">
      <span style="font-size:28px;font-weight:700;
                   color:#FFD700;letter-spacing:2px;
                   font-family:monospace;">🔷 ABHI-NEXUS</span>
      <span style="font-size:12px;color:#8B6914;
                   font-family:monospace;margin-left:16px;">
        PERSONAL TECH INTELLIGENCE · MULTI-AGENT SYSTEM
      </span>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    if st.session_state.role == "admin":
        tab1, tab2 = st.tabs(["📰 NEWS FEED", "⚙ ADMIN PANEL"])
        with tab1:
            render_news_feed()
        with tab2:
            render_admin_panel()
    else:
        render_news_feed()


# ── Entry point ────────────────────────────────

def main():
    if st.session_state.token is None:
        render_login()
    else:
        render_main()

main()
