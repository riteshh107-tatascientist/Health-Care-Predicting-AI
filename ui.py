"""Shared visual system: light healthcare theme, animations, cards, splash and welcome ribbon."""
from __future__ import annotations

import base64
import time
from functools import lru_cache
from html import escape

import streamlit as st

import config

CSS = """
:root{--navy:#0b3d6e;--navy-2:#06254a;--teal:#0f9b8e;--teal-2:#14b8a6;--ink:#0b2545;--muted:#4b5b70;--line:#e2ecf5;--amber:#f59e0b;--red:#b42318}
.stApp{background:radial-gradient(1100px 520px at 0% -10%,#e4f3ff 0%,transparent 60%),radial-gradient(900px 480px at 110% 0%,#dff7f2 0%,transparent 55%),#f4f8fb;color:var(--ink)}
.stApp p,.stApp li,.stApp label,.stApp span,.stApp td,.stApp th{color:var(--ink)}
h1,h2,h3,h4{color:var(--navy)!important;letter-spacing:-.01em}
.block-container{padding-top:1.6rem;max-width:1280px}
section[data-testid="stSidebar"]{background:linear-gradient(185deg,#0b3d6e 0%,#06254a 70%,#052040 100%)!important;border-right:1px solid rgba(255,255,255,.06)}
section[data-testid="stSidebar"] *{color:#e9f5ff}
section[data-testid="stSidebar"] [data-testid="stRadioOption"]{display:flex!important;align-items:center;padding:.55rem .8rem;border-radius:12px;margin:.18rem 0;border:1px solid transparent;transition:all .25s ease;cursor:pointer}
section[data-testid="stSidebar"] [data-testid="stRadioOption"]>div>div:first-child{display:none!important}
section[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover{background:rgba(20,184,166,.16);transform:translateX(4px)}
section[data-testid="stSidebar"] div[data-selected="true"]>[data-testid="stRadioOption"]{background:linear-gradient(90deg,rgba(20,184,166,.40),rgba(20,184,166,.10));border-color:rgba(94,234,212,.65);animation:glow 2.4s ease-in-out infinite;font-weight:600}
@keyframes glow{0%,100%{box-shadow:0 0 8px rgba(45,212,191,.30)}50%{box-shadow:0 0 22px rgba(45,212,191,.70)}}
.hx-brand{display:flex;align-items:center;gap:.7rem;padding:.4rem .2rem 1rem .2rem;border-bottom:1px solid rgba(255,255,255,.12);margin-bottom:.8rem}
.hx-brand-mark{width:44px;height:44px;border-radius:14px;background:linear-gradient(135deg,#5eead4,#14b8a6);display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:800;color:#06254a!important;box-shadow:0 0 18px rgba(94,234,212,.5);animation:pulse 2.6s ease-in-out infinite}
.hx-brand small{opacity:.75}
.hx-user{margin-top:1rem;padding:.8rem;border-radius:14px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12)}
.hx-chip{display:inline-block;padding:.15rem .6rem;border-radius:999px;background:rgba(94,234,212,.2);color:#ccfbf1!important;font-size:.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.hx-hero{position:relative;overflow:hidden;display:flex;gap:2rem;align-items:center;justify-content:space-between;background:linear-gradient(135deg,#06254a 0%,#0b3d6e 48%,#0f9b8e 100%);border-radius:26px;padding:2.6rem 2.6rem;box-shadow:0 24px 60px rgba(11,61,110,.28);animation:fadeUp .7s ease both;margin-bottom:1.4rem}
.hx-hero::after{content:"";position:absolute;inset:0;background:linear-gradient(110deg,transparent 30%,rgba(255,255,255,.16) 50%,transparent 70%);background-size:200% 100%;animation:shimmer 5s linear infinite;pointer-events:none}
.hx-hero h1,.hx-hero h2,.hx-hero h3,.hx-hero p,.hx-hero span,.hx-hero div{color:#fff!important}
.hx-hero h1{font-size:2.35rem;line-height:1.15;margin:.5rem 0 .8rem 0;font-weight:800}
.hx-hero p{font-size:1.02rem;opacity:.95;margin:.3rem 0}
.hx-eyebrow{display:inline-block;padding:.25rem .8rem;border-radius:999px;background:rgba(255,255,255,.14);font-size:.82rem;letter-spacing:.05em;font-weight:600}
.hx-founder{margin-top:1rem!important;font-weight:600;border-top:1px solid rgba(255,255,255,.25);padding-top:.7rem;display:inline-block}
.hx-hero-art{width:min(340px,38%);animation:float 6s ease-in-out infinite}
.hx-card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:1.15rem 1.25rem;box-shadow:0 10px 28px rgba(11,61,110,.08);transition:transform .25s ease,box-shadow .25s ease;animation:fadeUp .6s ease both;height:100%}
.hx-card:hover{transform:translateY(-4px);box-shadow:0 18px 40px rgba(11,61,110,.16)}
.hx-card h4{margin:.1rem 0 .35rem 0;color:var(--navy)!important;font-size:1.05rem}
.hx-card p,.hx-card li,.hx-card small,.hx-card span{color:var(--muted)!important}
.hx-card .hx-big{color:var(--navy)!important;font-weight:700}
.hx-step{display:flex;gap:.8rem;align-items:flex-start}
.hx-step-num{min-width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#0b3d6e,#0f9b8e);color:#fff!important;display:flex;align-items:center;justify-content:center;font-weight:700}
.hx-leader{display:flex;gap:1.8rem;align-items:center;background:linear-gradient(120deg,#fff,#f0faf8);border:1px solid var(--line);border-radius:22px;padding:1.6rem;box-shadow:0 14px 34px rgba(11,61,110,.1)}
.hx-portrait{width:190px;height:190px;border-radius:50%;object-fit:cover;object-position:center 30%;border:5px solid #fff;box-shadow:0 16px 36px rgba(11,61,110,.35);flex-shrink:0;animation:fadeUp .8s ease both}
.hx-ribbon{position:relative;overflow:hidden;background:linear-gradient(90deg,#0f9b8e,#0b3d6e,#0f9b8e);background-size:200% 100%;color:#fff!important;border-radius:16px;padding:1rem 1.4rem;font-weight:700;font-size:1.08rem;box-shadow:0 14px 30px rgba(15,155,142,.35);animation:ribbonIn 1s cubic-bezier(.2,.8,.2,1) both,bgMove 4s linear infinite;margin:.4rem 0 1rem 0}
.hx-ribbon *{color:#fff!important}
.hx-ribbon::after{content:"";position:absolute;top:0;bottom:0;width:40%;left:-60%;background:linear-gradient(100deg,transparent,rgba(255,255,255,.35),transparent);animation:sweep 2.6s ease-in-out infinite}
.hx-disclaimer{background:#fff8e6;border-left:5px solid var(--amber);color:#5b3d00!important;border-radius:12px;padding:.75rem 1rem;margin:.6rem 0 1rem 0;font-size:.92rem}
.hx-disclaimer *{color:#5b3d00!important}
.hx-note{background:#eef6ff;border-left:5px solid #2563eb;border-radius:12px;padding:.7rem 1rem;margin:.5rem 0}
.hx-emergency{background:linear-gradient(135deg,#b42318,#7a1310);border-radius:18px;padding:1.1rem 1.3rem;box-shadow:0 14px 30px rgba(180,35,24,.3);margin:.6rem 0 1rem 0}
.hx-emergency,.hx-emergency *{color:#fff!important}
.hx-badge{display:inline-block;padding:.2rem .7rem;border-radius:999px;font-size:.78rem;font-weight:600;background:#e0f2fe;color:#075985!important;margin-bottom:.4rem}
.hx-status-scheduled{background:#e0f2fe;color:#075985!important}
.hx-status-confirmed{background:#dcfce7;color:#166534!important}
.hx-status-completed{background:#ede9fe;color:#5b21b6!important}
.hx-status-cancelled{background:#fee2e2;color:#991b1b!important}
.hx-status-open{background:#fff7ed;color:#9a3412!important}
.hx-status-in-progress{background:#e0f2fe;color:#075985!important}
.hx-status-resolved{background:#dcfce7;color:#166534!important}
.hx-status-scheduled,.hx-status-confirmed,.hx-status-completed,.hx-status-cancelled,.hx-status-open,.hx-status-in-progress,.hx-status-resolved{padding:.15rem .6rem;border-radius:999px;font-size:.78rem;font-weight:700;display:inline-block}
.hx-page-title{display:flex;align-items:center;gap:.7rem;margin-bottom:.1rem}
.hx-page-title h2{margin:0!important}
.hx-subtitle{color:var(--muted)!important;margin-bottom:1rem}
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{background:linear-gradient(90deg,#0b3d6e,#0f9b8e)!important;color:#fff!important;border:none!important;border-radius:12px!important;padding:.55rem 1.2rem!important;font-weight:600!important;box-shadow:0 6px 16px rgba(11,61,110,.22);transition:all .2s ease}
.stButton>button p,.stFormSubmitButton>button p,.stDownloadButton>button p{color:#fff!important}
.stButton>button:hover,.stFormSubmitButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);box-shadow:0 12px 24px rgba(15,155,142,.35)}
[data-testid="stMetric"]{background:#fff;border-radius:16px;padding:.8rem 1rem;border:1px solid var(--line);box-shadow:0 8px 22px rgba(11,61,110,.07);animation:fadeUp .5s ease both}
[data-testid="stMetricValue"]{color:var(--navy)!important}
[data-testid="stMetricLabel"] p{color:var(--muted)!important}
.stTabs [data-baseweb="tab-list"]{gap:.4rem}
.stTabs [data-baseweb="tab"]{font-weight:600;border-radius:10px 10px 0 0}
[data-testid="stForm"]{background:#fff;border:1px solid var(--line);border-radius:18px;padding:1rem 1.2rem;box-shadow:0 8px 22px rgba(11,61,110,.06)}
div[data-testid="stExpander"]{background:#fff;border-radius:14px;border:1px solid var(--line)}
.hx-splash{position:fixed;inset:0;z-index:99999;display:flex;flex-direction:column;align-items:center;justify-content:center;background:linear-gradient(135deg,#06254a,#0b3d6e 55%,#0f9b8e);animation:splashOut .6s ease 1.9s forwards}
.hx-splash-logo{width:92px;height:92px;border-radius:26px;background:linear-gradient(135deg,#5eead4,#14b8a6);display:flex;align-items:center;justify-content:center;font-size:48px;font-weight:800;color:#06254a;animation:pulse 1.2s ease-in-out infinite;box-shadow:0 0 40px rgba(94,234,212,.6)}
.hx-splash-title{color:#fff;font-size:2.3rem;font-weight:800;margin-top:1.2rem;animation:fadeUp .8s ease both}
.hx-splash-sub{color:#bfeee8;margin-top:.3rem;animation:fadeUp 1s ease both}
.hx-splash-bar{width:260px;height:6px;background:rgba(255,255,255,.2);border-radius:99px;overflow:hidden;margin-top:26px}
.hx-splash-bar span{display:block;height:100%;width:0;background:linear-gradient(90deg,#5eead4,#fff);animation:load 2s ease forwards}
.hx-footer{text-align:center;color:var(--muted)!important;font-size:.85rem;padding:1.2rem 0 .4rem 0;border-top:1px solid var(--line);margin-top:2rem}
.hx-footer *{color:var(--muted)!important}
@keyframes load{to{width:100%}}
@keyframes splashOut{to{opacity:0;visibility:hidden}}
@keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes ribbonIn{from{transform:translateX(-40px);opacity:0}to{transform:none;opacity:1}}
@keyframes bgMove{from{background-position:0 0}to{background-position:200% 0}}
@keyframes sweep{from{left:-60%}to{left:120%}}
@keyframes shimmer{0%{background-position:-100% 0}100%{background-position:100% 0}}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
@media (max-width:820px){.hx-hero{flex-direction:column;padding:1.5rem}.hx-hero h1{font-size:1.7rem}.hx-hero-art{width:70%}.hx-leader{flex-direction:column;text-align:center}.hx-splash-title{font-size:1.6rem}}
"""

SPLASH_HTML = (
    '<div class="hx-splash"><div class="hx-splash-logo">✚</div>'
    '<div class="hx-splash-title">HealthCareX</div>'
    '<div class="hx-splash-sub">Compassionate Care · Smarter Healthcare · Better Patient Support</div>'
    '<div class="hx-splash-bar"><span></span></div></div>'
)

HERO_ART = (
    '<svg class="hx-hero-art" viewBox="0 0 340 300" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<defs><linearGradient id="g1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5eead4"/>'
    '<stop offset="1" stop-color="#ffffff"/></linearGradient></defs>'
    '<rect x="40" y="60" width="260" height="190" rx="26" fill="rgba(255,255,255,.12)" stroke="rgba(255,255,255,.35)"/>'
    '<rect x="95" y="28" width="150" height="46" rx="10" fill="rgba(255,255,255,.18)"/>'
    '<rect x="140" y="110" width="60" height="150" rx="8" fill="url(#g1)" opacity=".95"/>'
    '<rect x="115" y="135" width="110" height="46" rx="8" fill="url(#g1)" opacity=".95"/>'
    '<path d="M48 205 L92 205 L110 175 L132 240 L160 150 L185 220 L205 205 L292 205" fill="none" '
    'stroke="#ffffff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" '
    'style="stroke-dasharray:600;stroke-dashoffset:600;animation:draw 2.4s ease forwards"/>'
    '<style>@keyframes draw{to{stroke-dashoffset:0}}</style></svg>'
)



EXTRA_CSS = """
[data-testid="stSidebar"] div[role="radiogroup"]{gap:.35rem}
[data-testid="stSidebar"] div[role="radiogroup"] > label{padding:.55rem .8rem;border-radius:14px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.05);transition:all .25s ease}
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover{background:rgba(94,234,212,.14);box-shadow:0 0 16px rgba(94,234,212,.35);transform:translateX(3px)}
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked){background:linear-gradient(135deg,rgba(20,184,166,.6),rgba(14,116,144,.6));box-shadow:0 0 22px rgba(94,234,212,.6);border-color:rgba(94,234,212,.75)}
[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child{display:none!important}
[data-testid="stSidebar"] .stButton>button{background:linear-gradient(135deg,#14b8a6,#0e7490);color:#fff!important;border:none;border-radius:14px;font-weight:700;box-shadow:0 0 16px rgba(20,184,166,.45);animation:glowPulse 3s ease-in-out infinite;transition:transform .2s ease}
[data-testid="stSidebar"] .stButton>button:hover{transform:translateY(-2px);box-shadow:0 0 28px rgba(94,234,212,.85)}
@keyframes glowPulse{0%,100%{box-shadow:0 0 12px rgba(20,184,166,.35)}50%{box-shadow:0 0 26px rgba(94,234,212,.75)}}
.hx-next{border-left:6px solid #0f9b8e}
@media (max-width: 768px){
  [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important;gap:.6rem!important}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{min-width:100%!important;flex:1 1 100%!important}
  .hcx-hero,.hx-hero{padding:22px 18px!important;border-radius:18px!important}
  .hcx-hero h1,.hx-hero h1,.hx-hero h2{font-size:1.45rem!important;line-height:1.25!important}
  .hcx-portrait,.hx-portrait{width:150px!important;height:150px!important}
  .block-container{padding-left:.9rem!important;padding-right:.9rem!important}
  h1{font-size:1.6rem!important} h2{font-size:1.3rem!important}
}
.hx-next .big{font-size:1.25rem;font-weight:700;color:#0b3d6e}
"""

def inject_css() -> None:
    st.markdown(f"<style>{CSS}{EXTRA_CSS}</style>", unsafe_allow_html=True)


def show_splash(seconds: float = 2.4) -> None:
    """Landing animation shown once per browser session."""
    slot = st.empty()
    slot.markdown(SPLASH_HTML, unsafe_allow_html=True)
    time.sleep(seconds)
    slot.empty()


@lru_cache(maxsize=1)
def portrait_data_uri() -> str | None:
    if not config.PORTRAIT_PATH.exists():
        return None
    encoded = base64.b64encode(config.PORTRAIT_PATH.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def hero(compact: bool = False, user: dict | None = None) -> None:
    greeting = f'<p>Welcome back, <b>{escape(user["name"])}</b>.</p>' if user else ""
    art = "" if compact else HERO_ART
    st.markdown(
        '<div class="hx-hero">'
        '<div style="position:relative;z-index:1;max-width:620px">'
        f'<span class="hx-eyebrow">✚ {escape(config.APP_NAME)}</span>'
        f'<h1>{escape(config.TAGLINE)}</h1>'
        f'<p>{escape(config.OWNER_STATEMENT)}</p>'
        f'<p class="hx-founder">Founded &amp; Managed by {escape(config.OWNER_NAME)}</p>'
        f'{greeting}'
        '</div>' + art + '</div>',
        unsafe_allow_html=True,
    )


def welcome_ribbon(name: str) -> None:
    st.markdown(
        f'<div class="hx-ribbon">🎉 Welcome to HealthCareX, {escape(name)}! Your account is ready — '
        'book appointments, store records and explore your health tools.</div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, icon: str = "") -> None:
    st.markdown(
        f'<div class="hx-page-title"><span style="font-size:1.8rem">{icon}</span><h2>{escape(title)}</h2></div>'
        f'<p class="hx-subtitle">{escape(subtitle)}</p>',
        unsafe_allow_html=True,
    )


def card(title: str, body: str, footer: str = "", icon: str = "") -> str:
    """Return card HTML; caller decides where to place it (st.markdown)."""
    footer_html = f'<p style="margin-top:.6rem"><small>{escape(footer)}</small></p>' if footer else ""
    return (f'<div class="hx-card"><h4>{icon} {escape(title)}</h4>'
            f'<p>{escape(body)}</p>{footer_html}</div>')


def show_card(title: str, body: str, footer: str = "", icon: str = "") -> None:
    st.markdown(card(title, body, footer, icon), unsafe_allow_html=True)


def disclaimer(text: str = config.DISCLAIMER_GENERAL) -> None:
    st.markdown(f'<div class="hx-disclaimer">⚠️ {escape(text)}</div>', unsafe_allow_html=True)


def emergency_banner() -> None:
    st.markdown(
        '<div class="hx-emergency"><h3 style="margin:0 0 .4rem 0">🚨 Emergency warning</h3>'
        f'<p style="margin:0;font-size:1.02rem">{escape(config.DISCLAIMER_EMERGENCY)}</p></div>',
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    css = status.replace(" ", "-")
    return f'<span class="hx-status-{css}">{escape(status.title())}</span>'


def demo_badge() -> None:
    if not config.DEMO_ENABLED:
        return
    st.markdown('<span class="hx-badge">Demo data for educational / testing purposes</span>', unsafe_allow_html=True)


def empty_state(message: str) -> None:
    st.info(message)


def sidebar_brand() -> None:
    st.markdown(
        '<div class="hx-brand"><div class="hx-brand-mark">✚</div>'
        f'<div><b style="font-size:1.1rem">{escape(config.APP_SHORT_NAME)}</b><br>'
        '<small>Medical &amp; Wellness Center</small></div></div>',
        unsafe_allow_html=True,
    )


def sidebar_user_card(user: dict) -> None:
    st.markdown(
        f'<div class="hx-user"><b>{escape(user["name"])}</b><br>'
        f'<span class="hx-chip">{escape(user["role"])}</span></div>',
        unsafe_allow_html=True,
    )


def leadership_section() -> None:
    uri = portrait_data_uri()
    image = (f'<img class="hx-portrait" src="{uri}" alt="Portrait of {escape(config.OWNER_NAME)}"/>'
             if uri else '<div class="hx-portrait" style="display:flex;align-items:center;justify-content:center;'
                         'background:#0b3d6e;color:#fff;font-size:64px">✚</div>')
    st.markdown(
        '<div class="hx-leader">' + image +
        '<div><span class="hx-eyebrow" style="background:#e0f2fe;color:#075985!important">Leadership</span>'
        f'<h2 style="margin:.6rem 0 .1rem 0">{escape(config.OWNER_NAME)}</h2>'
        f'<h4 style="margin:0 0 .6rem 0;color:#0f9b8e!important">{escape(config.OWNER_TITLE)}</h4>'
        f'<p style="color:#4b5b70!important;font-size:1.02rem">{escape(config.OWNER_STATEMENT)}</p>'
        '<p style="color:#4b5b70!important;margin-top:.6rem">Leading HealthCareX with a patient-first approach: '
        'clear access to services, respectful records handling, and honest, educational digital tools.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def footer() -> None:
    st.markdown(
        f'<div class="hx-footer"><b>{escape(config.APP_NAME)}</b> · Version {escape(config.APP_VERSION)}<br>'
        f'Founded &amp; Managed by {escape(config.OWNER_NAME)}<br>'
        f'{escape(config.DISCLAIMER_GENERAL)}</div>',
        unsafe_allow_html=True,
    )
