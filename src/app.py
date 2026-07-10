import os
import sys
import json
import time
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.schemas import FinalDecision
from src.graph import build_graph, MAX_STEPS
from src.guardrails import fairness_check

load_dotenv()

st.set_page_config(
    page_title="TechVest Recruitment Agent",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── PREMIUM DESIGN SYSTEM —──────────────────────────────────────────────────

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Design Tokens ── */
:root {
    --color-text-primary: #111827;
    --color-text-secondary: #475569;
    --color-text-muted: #64748b;
    --color-text-disabled: #94a3b8;
    --color-text-inverse: #ffffff;
    --color-text-inverse-soft: rgba(255,255,255,0.88);
    --color-bg-page: #f6f7fb;
    --color-bg-card: #ffffff;
    --color-bg-card-elevated: #ffffff;
    --color-bg-muted: #f8f9fc;
    --color-border: #e2e8f0;
    --color-border-soft: #eef0f4;
    --color-accent: #6366f1;
    --color-accent-hover: #4f46e5;
    --color-success: #16a34a;
    --color-warning: #d97706;
    --color-danger: #dc2626;
    --color-info: #2563eb;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
    --shadow-lg: 0 12px 40px rgba(0,0,0,0.1);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 20px;
    --radius-pill: 100px;
}

/* ── Reset & Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--color-text-primary);
}

.stApp {
    background: var(--color-bg-page);
    background-image:
        radial-gradient(ellipse at 0% 0%, rgba(99, 102, 241, 0.04) 0%, transparent 50%),
        radial-gradient(ellipse at 100% 0%, rgba(139, 92, 246, 0.04) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 100%, rgba(59, 130, 246, 0.03) 0%, transparent 50%);
}

/* ── Typography Scale ── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif;
    letter-spacing: -0.02em;
    color: var(--color-text-primary);
}

/* ── Hide Streamlit Branding ── */
#MainMenu, footer, header { display: none !important; }
.stAppToolbar { display: none !important; }

/* ── Premium Header ── */
.premium-header {
    background: linear-gradient(135deg, #0c0c1d 0%, #1a1a3e 25%, #0f172a 50%, #0f3460 100%);
    padding: 2.2rem 2.8rem;
    border-radius: 24px;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 25px 70px rgba(15, 12, 41, 0.2);
    border: 1px solid rgba(255,255,255,0.06);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.premium-header:hover {
    box-shadow: 0 30px 80px rgba(15, 12, 41, 0.25);
    transform: translateY(-1px);
}
.premium-header::before {
    content: '';
    position: absolute;
    top: -60%;
    right: -15%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, rgba(99, 102, 241, 0.04) 30%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
    animation: float-glow 8s ease-in-out infinite;
}
.premium-header::after {
    content: '';
    position: absolute;
    bottom: -40%;
    left: -10%;
    width: 350px;
    height: 350px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.08) 0%, rgba(139, 92, 246, 0.02) 30%, transparent 70%);
    border-radius: 50%;
    pointer-events: none;
    animation: float-glow 10s ease-in-out infinite reverse;
}
@keyframes float-glow {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(10px, -10px) scale(1.05); }
    66% { transform: translate(-5px, 5px) scale(0.95); }
}
.premium-header .header-content {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 1rem;
    position: relative;
    z-index: 1;
}
.premium-header h1 {
    color: #fff !important;
    font-weight: 800;
    font-size: 2.4rem;
    margin: 0;
    letter-spacing: -1px;
    background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 50%, #c4b5fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.15;
}
.premium-header .subtitle {
    color: var(--color-text-inverse-soft);
    margin: 6px 0 0 0;
    font-size: 0.95rem;
    font-weight: 400;
    letter-spacing: 0.1px;
}
.premium-header .header-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.15);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.18);
    padding: 6px 18px;
    border-radius: 100px;
    font-size: 0.75rem;
    color: var(--color-text-inverse-soft);
    margin-top: 12px;
    transition: all 0.3s ease;
    cursor: default;
}
.premium-header .header-badge:hover {
    background: rgba(255,255,255,0.22);
    border-color: rgba(255,255,255,0.3);
}
.premium-header .header-badge .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #4ade80;
    animation: pulse-dot 2s ease-in-out infinite;
    box-shadow: 0 0 8px rgba(74, 222, 128, 0.4);
}
.premium-header .header-actions {
    display: flex;
    gap: 10px;
    align-items: center;
}

/* ── Glow Orb ── */
.glow-orb {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
}
.glow-orb.green { background: #4ade80; box-shadow: 0 0 10px rgba(74, 222, 128, 0.5); }
.glow-orb.amber { background: #fbbf24; box-shadow: 0 0 10px rgba(251, 191, 36, 0.5); }
.glow-orb.blue { background: #60a5fa; box-shadow: 0 0 10px rgba(96, 165, 250, 0.5); }
.glow-orb.purple { background: #a78bfa; box-shadow: 0 0 10px rgba(167, 139, 250, 0.5); }
.glow-orb.red { background: #f87171; box-shadow: 0 0 10px rgba(248, 113, 113, 0.5); }

/* ── Core Animations ── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
@keyframes slideInRight {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
}
@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.8; transform: scale(0.9); }
}
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-6px); }
}
@keyframes progress-fill {
    from { width: 0%; }
}
@keyframes countUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes spin-slow {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
@keyframes breathing-border {
    0%, 100% { border-color: rgba(99, 102, 241, 0.15); }
    50% { border-color: rgba(99, 102, 241, 0.35); }
}

/* ── Entrance Classes ── */
.animate-fade-in { animation: fadeInUp 0.5s ease-out both; }
.animate-fade-in-delay-1 { animation: fadeInUp 0.5s ease-out 0.1s both; }
.animate-fade-in-delay-2 { animation: fadeInUp 0.5s ease-out 0.2s both; }
.animate-fade-in-delay-3 { animation: fadeInUp 0.5s ease-out 0.3s both; }
.animate-fade-in-delay-4 { animation: fadeInUp 0.5s ease-out 0.4s both; }
.animate-fade-in-delay-5 { animation: fadeInUp 0.5s ease-out 0.5s both; }
.animate-scale-in {
    animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}
.animate-slide-right {
    animation: slideInRight 0.4s ease-out forwards;
}

/* ── Glass Card ── */
.glass-card {
    background: rgba(255,255,255,0.97);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: 1px solid var(--color-border-soft);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    box-shadow:
        0 1px 3px var(--shadow-sm),
        0 4px 12px var(--shadow-md);
    transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.glass-card:hover {
    box-shadow:
        0 2px 6px rgba(0,0,0,0.06),
        0 8px 24px rgba(0,0,0,0.08),
        0 20px 60px rgba(0,0,0,0.1);
    transform: translateY(-2px);
}
.glass-card.interactive {
    cursor: pointer;
}
.glass-card.interactive:active {
    transform: translateY(0px) scale(0.98);
}

/* ── Premium Card (Solid) ── */
.premium-card {
    background: var(--color-bg-card);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-sm);
    transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.premium-card:hover {
    box-shadow: 0 8px 30px rgba(0,0,0,0.1);
    transform: translateY(-2px);
    border-color: var(--color-border);
}
.premium-card .accent-bar {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    border-radius: 0 0 2px 2px;
}
.premium-card .accent-bar.interview {
    background: linear-gradient(90deg, #4ade80, #22c55e, #16a34a);
}
.premium-card .accent-bar.hold {
    background: linear-gradient(90deg, #fbbf24, #f59e0b, #d97706);
}
.premium-card .accent-bar.reject {
    background: linear-gradient(90deg, #f87171, #ef4444, #dc2626);
}

/* ── Verdict Badge ── */
.verdict-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 16px;
    border-radius: var(--radius-pill);
    font-weight: 600;
    font-size: 0.72rem;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    transition: all 0.25s ease;
}
.verdict-badge.interview {
    background: #dcfce7;
    color: #166534;
    border: 1px solid #86efac;
    box-shadow: 0 2px 8px rgba(34, 197, 94, 0.15);
}
.verdict-badge.hold {
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #fcd34d;
    box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15);
}
.verdict-badge.reject {
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #fca5a5;
    box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
}
.verdict-badge:hover {
    transform: translateY(-1px) scale(1.02);
}

/* ── Avatar ── */
.candidate-avatar {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 1rem;
    flex-shrink: 0;
    transition: all 0.3s ease;
}
.candidate-avatar.interview {
    background: #dcfce7;
    color: #166534;
    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.2);
}
.candidate-avatar.hold {
    background: #fef3c7;
    color: #92400e;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2);
}
.candidate-avatar.reject {
    background: #fee2e2;
    color: #991b1b;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
}

/* ── Score Ring ── */
.score-ring-container {
    position: relative;
    width: 76px;
    height: 76px;
    flex-shrink: 0;
}
.score-ring-svg {
    transform: rotate(-90deg);
    width: 76px;
    height: 76px;
}
.score-ring-bg {
    fill: none;
    stroke: #eef0f4;
    stroke-width: 5;
}
.score-ring-fill {
    fill: none;
    stroke-width: 5;
    stroke-linecap: round;
    transition: stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1);
    filter: drop-shadow(0 2px 4px rgba(99,102,241,0.2));
}
.score-ring-fill.high { stroke: #22c55e; }
.score-ring-fill.mid { stroke: #f59e0b; }
.score-ring-fill.low { stroke: #ef4444; }
.score-ring-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-weight: 700;
    font-size: 1.15rem;
    color: #1a1a2e;
    letter-spacing: -0.5px;
}

/* ── Metric Card ── */
.metric-card {
    background: var(--color-bg-card);
    border-radius: var(--radius-md);
    padding: 1.3rem;
    border: 1px solid var(--color-border);
    text-align: center;
    box-shadow: var(--shadow-sm);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: 0 0 2px 2px;
}
.metric-card.metric-interview::before { background: linear-gradient(90deg, #4ade80, #22c55e); }
.metric-card.metric-hold::before { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
.metric-card.metric-reject::before { background: linear-gradient(90deg, #f87171, #ef4444); }
.metric-card.metric-default::before { background: linear-gradient(90deg, #6366f1, #8b5cf6); }
.metric-card:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,0.1);
    transform: translateY(-3px);
}
.metric-card .label {
    font-size: 0.68rem;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 600;
    margin-bottom: 2px;
}
.metric-card .value {
    font-size: 1.8rem;
    font-weight: 800;
    line-height: 1.2;
    letter-spacing: -0.5px;
    color: var(--color-text-primary);
}

/* ── Pill Container ── */
.pill-container {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 1.2rem;
}
.pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: var(--color-bg-card);
    padding: 6px 18px;
    border-radius: var(--radius-pill);
    font-size: 0.76rem;
    font-weight: 500;
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.pill:hover {
    background: var(--color-bg-card);
    border-color: #cbd5e1;
    transform: translateY(-1.5px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}

/* ── Buttons ── */
.stButton button {
    border-radius: var(--radius-md) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 1.5rem !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    border: none !important;
    letter-spacing: 0.2px !important;
    position: relative !important;
    overflow: hidden !important;
}
.stButton button::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(255,255,255,0.25);
    transition: all 0.4s ease;
    transform: translate(-50%, -50%);
}
.stButton button:hover::after {
    width: 200px;
    height: 200px;
}
.stButton button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(0,0,0,0.15) !important;
}
.stButton button:active {
    transform: translateY(0px) scale(0.97) !important;
}
.stButton button:disabled,
.stButton button:disabled:hover {
    opacity: 0.55 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
}
.stButton button:disabled::after {
    display: none !important;
}
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%) !important;
    color: #fff !important;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3) !important;
}
.stButton button[kind="primary"]:hover {
    box-shadow: 0 8px 32px rgba(99, 102, 241, 0.45) !important;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #8b5cf6 100%) !important;
}
.stButton button[kind="secondary"] {
    background: var(--color-bg-card) !important;
    color: var(--color-text-primary) !important;
    border: 1px solid var(--color-border) !important;
    box-shadow: var(--shadow-sm) !important;
}
.stButton button[kind="secondary"]:hover {
    background: var(--color-bg-card) !important;
    border-color: #cbd5e1 !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 3px;
    background: var(--color-bg-card);
    border-radius: var(--radius-md);
    padding: 5px;
    border: 1px solid var(--color-border-soft);
    margin-bottom: 1.2rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 8px 22px !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    color: var(--color-text-muted) !important;
    transition: all 0.25s ease !important;
    border: none !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--color-text-primary) !important;
    background: rgba(99, 102, 241, 0.06) !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--color-bg-card) !important;
    color: var(--color-accent) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    font-weight: 700 !important;
}

/* ── Expander ── */
div.stExpander {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--color-border) !important;
    box-shadow: var(--shadow-sm) !important;
    margin-bottom: 10px !important;
    transition: all 0.25s ease !important;
    background: var(--color-bg-card) !important;
}
div.stExpander:hover {
    box-shadow: 0 6px 20px rgba(0,0,0,0.08) !important;
    border-color: var(--color-border) !important;
}
div.stExpander details summary {
    font-weight: 600 !important;
    padding: 0.9rem 1.2rem !important;
    font-size: 0.9rem !important;
    color: var(--color-text-primary) !important;
}
div.stExpander details[open] summary {
    border-bottom: 1px solid var(--color-border-soft) !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--color-bg-card) !important;
    border-right: 1px solid var(--color-border) !important;
    box-shadow: 4px 0 32px rgba(0,0,0,0.06) !important;
}
section[data-testid="stSidebar"] .stMarkdown h3 {
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--color-text-muted);
    font-weight: 600;
    margin-top: 1.2rem !important;
}
section[data-testid="stSidebar"] .stMarkdown p {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
}

/* ── Text Inputs ── */
.stTextInput input, .stTextArea textarea {
    border-radius: var(--radius-md) !important;
    border: 1.5px solid var(--color-border) !important;
    padding: 0.65rem 1rem !important;
    font-size: 0.9rem !important;
    transition: all 0.25s ease !important;
    background: var(--color-bg-card) !important;
    box-shadow: var(--shadow-sm) !important;
    color: var(--color-text-primary) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--color-accent) !important;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12) !important;
}
.stTextInput input:hover, .stTextArea textarea:hover {
    border-color: #cbd5e1 !important;
}

/* ── Select ── */
.stSelectbox div[data-baseweb="select"] {
    border-radius: var(--radius-md) !important;
    border: 1.5px solid var(--color-border) !important;
    box-shadow: var(--shadow-sm) !important;
    transition: all 0.2s ease !important;
}
.stSelectbox div[data-baseweb="select"]:hover {
    border-color: #cbd5e1 !important;
}

/* ── Toggle ── */
.stToggle label {
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    color: var(--color-text-primary) !important;
}

/* ── Divider ── */
hr {
    margin: 1.2rem 0 !important;
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--color-border), transparent) !important;
}

/* ── Code Block ── */
.stCodeBlock {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--color-border) !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ── Alert / Info ── */
div[role="alert"] {
    border-radius: var(--radius-md) !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
    padding: 1rem 1.2rem !important;
}

/* ── Skeleton Loading ── */
.skeleton {
    background: linear-gradient(90deg, #e2e8f0 25%, #cbd5e1 50%, #e2e8f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
    border-radius: 10px;
}
.skeleton-line {
    height: 14px;
    margin-bottom: 10px;
    width: 100%;
}
.skeleton-line.short { width: 55%; }
.skeleton-line.medium { width: 75%; }
.skeleton-line.long { width: 90%; }
.skeleton-circle {
    width: 56px;
    height: 56px;
    border-radius: 50%;
}
.skeleton-card {
    background: var(--color-bg-card);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    border: 1px solid var(--color-border);
    margin-bottom: 1rem;
}

/* ── Loading Animation ── */
.loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    text-align: center;
}
.loading-spinner {
    width: 48px;
    height: 48px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-accent);
    border-radius: 50%;
    animation: spin-slow 0.8s linear infinite;
    margin-bottom: 1.2rem;
}
.loading-spinner-fast {
    width: 20px;
    height: 20px;
    border: 2.5px solid rgba(255,255,255,0.5);
    border-top-color: #ffffff;
    border-radius: 50%;
    animation: spin-slow 0.6s linear infinite;
    display: inline-block;
}

/* ── Floating Action Button ── */
.fab {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    width: 58px;
    height: 58px;
    border-radius: 18px;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    box-shadow: 0 8px 32px rgba(99, 102, 241, 0.35);
    border: none;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 999;
    opacity: 0;
    animation: fadeInUp 0.5s ease-out 0.8s both;
    text-decoration: none;
}
.fab:hover {
    transform: translateY(-4px) scale(1.05);
    box-shadow: 0 12px 44px rgba(99, 102, 241, 0.45);
}
.fab:active {
    transform: translateY(-1px) scale(0.98);
}

/* ── Progress Bar ── */
.stProgress > div > div {
    border-radius: var(--radius-pill) !important;
    background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 60%, #a78bfa 100%) !important;
    transition: width 0.5s ease !important;
}

/* ── Tooltip ── */
.tooltip-trigger {
    position: relative;
    cursor: help;
    border-bottom: 1px dashed #94a3b8;
}
.tooltip-trigger:hover .tooltip-content {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
}
.tooltip-content {
    position: absolute;
    bottom: calc(100% + 10px);
    left: 50%;
    transform: translateX(-50%) translateY(6px);
    background: #1a1a2e;
    color: #fff;
    padding: 10px 16px;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 400;
    line-height: 1.4;
    white-space: nowrap;
    opacity: 0;
    visibility: hidden;
    transition: all 0.2s ease;
    pointer-events: none;
    z-index: 1100;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.tooltip-content::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: #1a1a2e;
}

/* ── Empty State ── */
.empty-state {
    text-align: center;
    padding: 3.5rem 2rem;
    animation: fadeInUp 0.5s ease-out;
}
.empty-state .icon-wrap {
    font-size: 3.5rem;
    margin-bottom: 1rem;
    color: var(--color-text-disabled);
    animation: float 3s ease-in-out infinite;
}
.empty-state h3 {
    color: var(--color-text-primary);
    font-weight: 600;
    margin-bottom: 0.5rem;
    font-size: 1.15rem;
}
.empty-state p {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    max-width: 420px;
    margin: 0 auto;
    line-height: 1.5;
}

/* ── Onboarding Steps ── */
.onboarding-flow {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 2rem 0 0.5rem;
    flex-wrap: wrap;
}
.onboarding-step {
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--color-bg-card);
    border-radius: var(--radius-md);
    padding: 12px 20px;
    border: 1px solid var(--color-border);
    font-size: 0.82rem;
    color: var(--color-text-secondary);
    transition: all 0.3s ease;
    box-shadow: var(--shadow-sm);
}
.onboarding-step:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    border-color: #cbd5e1;
}
.onboarding-step.active {
    background: #eef2ff;
    border-color: rgba(99, 102, 241, 0.3);
    color: #4338ca;
    font-weight: 600;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.15);
}
.onboarding-step .step-num {
    width: 26px;
    height: 26px;
    border-radius: 8px;
    background: var(--color-bg-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.75rem;
    color: var(--color-text-muted);
    transition: all 0.3s ease;
}
.onboarding-step.active .step-num {
    background: var(--color-accent);
    color: #fff;
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}
.onboarding-arrow {
    font-size: 1.2rem;
    color: #cbd5e1;
    margin: 0 4px;
    flex-shrink: 0;
}

/* ── Trajectory Stepper ── */
.traj-step {
    display: flex;
    gap: 14px;
    padding: 14px 0;
    border-left: 2px solid var(--color-border);
    margin-left: 14px;
    padding-left: 24px;
    position: relative;
    transition: all 0.25s ease;
}
.traj-step:last-child {
    border-left-color: transparent;
}
.traj-step::before {
    content: '';
    position: absolute;
    left: -8px;
    top: 18px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--color-border);
    border: 3px solid #fff;
    transition: all 0.3s ease;
}
.traj-step.active::before {
    background: var(--color-accent);
    box-shadow: 0 0 0 5px rgba(99, 102, 241, 0.2);
    border-color: #f8f9fc;
}
.traj-step:hover::before {
    transform: scale(1.2);
}
.traj-step .step-number {
    font-size: 0.68rem;
    font-weight: 700;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    min-width: 55px;
    padding-top: 2px;
}
.traj-step .step-content {
    flex: 1;
}
.traj-step .step-action {
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--color-text-primary);
    font-family: 'JetBrains Mono', monospace;
}
.traj-step .step-thought {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    margin-top: 3px;
    line-height: 1.4;
}

/* ── Score Bar ── */
.score-bar-track {
    height: 8px;
    background: var(--color-border-soft);
    border-radius: var(--radius-pill);
    overflow: hidden;
    position: relative;
}
.score-bar-fill {
    height: 100%;
    border-radius: 100px;
    transition: width 1.2s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
}
.score-bar-fill.high { 
    background: linear-gradient(90deg, #4ade80, #22c55e);
    box-shadow: 0 0 12px rgba(34, 197, 94, 0.3);
}
.score-bar-fill.mid { 
    background: linear-gradient(90deg, #fbbf24, #f59e0b);
    box-shadow: 0 0 12px rgba(245, 158, 11, 0.3);
}
.score-bar-fill.low { 
    background: linear-gradient(90deg, #f87171, #ef4444);
    box-shadow: 0 0 12px rgba(239, 68, 68, 0.3);
}

/* ── Fairness Card ── */
.fairness-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    padding: 16px 20px;
    border-radius: var(--radius-md);
    margin-bottom: 12px;
    border: 1px solid;
    transition: all 0.3s ease;
}
.fairness-card.passed {
    background: #f0fdf4;
    border-color: #86efac;
}
.fairness-card.failed {
    background: #fef2f2;
    border-color: #fca5a5;
}
.fairness-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.04);
}

/* ── Step Navigation ── */
.step-nav-container {
    background: var(--color-bg-card);
    border-radius: var(--radius-md);
    padding: 1rem 1.2rem;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-sm);
    margin-bottom: 1rem;
}
.step-nav-container .step-indicator {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--color-accent);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Interview Proposal ── */
.interview-proposal {
    background: #eef2ff;
    border-radius: var(--radius-md);
    padding: 12px 16px;
    border: 1px solid rgba(99, 102, 241, 0.2);
    margin-top: 10px;
    transition: all 0.3s ease;
}
.interview-proposal:hover {
    border-color: rgba(99, 102, 241, 0.35);
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.12);
}

/* ── Guardrail Card ── */
.guardrail-card {
    background: var(--color-bg-card);
    border-radius: var(--radius-lg);
    padding: 1.4rem;
    border: 1px solid var(--color-border);
    text-align: center;
    transition: all 0.3s ease;
    animation: fadeInUp 0.3s ease-out both;
}
.guardrail-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 28px rgba(0,0,0,0.1);
    border-color: #cbd5e1;
}
.guardrail-card .guardrail-icon {
    font-size: 2.2rem;
    margin-bottom: 0.7rem;
}
.guardrail-card .guardrail-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.guardrail-card .guardrail-value {
    font-size: 1.4rem;
    font-weight: 700;
    margin-bottom: 6px;
    color: var(--color-text-primary);
}
.guardrail-card .guardrail-desc {
    font-size: 0.72rem;
    color: var(--color-text-secondary);
    line-height: 1.4;
}

/* ── Responsive ── */
@media (max-width: 768px) {
    .premium-header { padding: 1.2rem 1.5rem; }
    .premium-header h1 { font-size: 1.5rem; }
    .candidate-card { padding: 1rem; }
    .onboarding-flow { flex-direction: column; gap: 8px; }
    .onboarding-arrow { transform: rotate(90deg); }
}
"""

st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

# ─── DATA LOADING ────────────────────────────────────────────────────────────

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def extract_text_from_file(uploaded_file):
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    if name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    elif name.endswith(".pdf"):
        from PyPDF2 import PdfReader
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif name.endswith(".docx"):
        import docx
        doc = docx.Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    return uploaded_file.read().decode("utf-8")


def load_defaults():
    with open(os.path.join(DEFAULT_DATA_DIR, "job_description.md"), "r", encoding="utf-8") as f:
        default_jd = f.read()
    with open(os.path.join(DEFAULT_DATA_DIR, "rubric.json"), "r", encoding="utf-8") as f:
        default_rubric = json.load(f)
    default_candidates = {}
    candidates_dir = os.path.join(DEFAULT_DATA_DIR, "candidates")
    for fname in os.listdir(candidates_dir):
        if fname.endswith(".md"):
            name = fname.replace(".md", "").title()
            with open(os.path.join(candidates_dir, fname), "r", encoding="utf-8") as f:
                default_candidates[name] = f.read()
    return default_jd, default_rubric, default_candidates


def suggest_criteria_from_jd(jd_text: str) -> dict:
    text_lower = jd_text.lower()
    keywords = {
        "Python": ["python"],
        "Machine Learning": ["machine learning", "ml", "deep learning", "neural", "model training", "supervised", "unsupervised", "classification", "regression"],
        "Data Engineering": ["data pipeline", "etl", "data processing", "sql", "database", "data warehouse", "big data", "spark"],
        "Cloud & DevOps": ["aws", "gcp", "azure", "cloud", "docker", "kubernetes", "ci/cd", "devops", "deployment"],
        "MLOps": ["mlops", "mlflow", "dvc", "experiment tracking", "model deployment", "model monitoring"],
        "Deep Learning": ["pytorch", "tensorflow", "keras", "transformer", "lstm", "cnn", "deep learning"],
        "NLP": ["nlp", "natural language", "text", "sentiment", "llm", "language model", "gpt"],
        "Communication": ["communication", "present", "stakeholder", "collaborate", "team", "mentor", "documentation"],
        "Frameworks & Tools": ["scikit-learn", "pandas", "numpy", "flask", "fastapi", "react", "node"],
        "Software Engineering": ["software", "microservice", "api", "rest", "testing", "code review", "agile", "git"],
        "Domain Knowledge": ["fintech", "finance", "healthcare", "e-commerce", "fraud", "recommendation"],
    }
    scale_templates = {
        "Python": {"0": "No Python", "1": "Basic syntax", "2": "Scripts with libraries", "3": "Built applications", "4": "Production code", "5": "Expert / OSS contributor"},
        "Machine Learning": {"0": "No ML knowledge", "1": "Theoretical familiarity", "2": "Coursework projects", "3": "Hands-on with real data", "4": "Production models", "5": "Published research"},
        "Data Engineering": {"0": "None", "1": "Basic SQL", "2": "Data scripts", "3": "Built pipelines", "4": "Production pipelines", "5": "Distributed systems"},
        "Cloud & DevOps": {"0": "None", "1": "Familiar", "2": "Used in projects", "3": "Deployed apps", "4": "Managed infrastructure", "5": "Expert"},
        "MLOps": {"0": "None", "1": "Aware", "2": "Used tools", "3": "Set up pipelines", "4": "Production MLOps", "5": "Designed systems"},
        "Deep Learning": {"0": "None", "1": "Familiar", "2": "Used frameworks", "3": "Built models", "4": "Deployed DL", "5": "Published"},
        "NLP": {"0": "None", "1": "Basic text processing", "2": "NLP projects", "3": "Production NLP", "4": "LLM experience", "5": "Published"},
        "Communication": {"0": "No evidence", "1": "Basic participation", "2": "Team contributor", "3": "Presented work", "4": "Mentors others", "5": "Leader / published"},
        "Frameworks & Tools": {"0": "None", "1": "1-2 tools", "2": "2-3 tools", "3": "Working proficiency", "4": "Deep stack", "5": "Contributor"},
        "Software Engineering": {"0": "None", "1": "Basic coding", "2": "Built features", "3": "Production apps", "4": "Microservices", "5": "Architect"},
        "Domain Knowledge": {"0": "None", "1": "Awareness", "2": "Some exposure", "3": "Working knowledge", "4": "Deep domain expertise", "5": "Industry authority"},
    }
    suggested = []
    matched = set()
    for criteria_name, kws in keywords.items():
        for kw in kws:
            if kw in text_lower and criteria_name not in matched:
                matched.add(criteria_name)
                scale = scale_templates.get(criteria_name, {"0": "None", "1": "Basic", "2": "Some", "3": "Good", "4": "Strong", "5": "Expert"})
                suggested.append({"name": criteria_name, "weight": 0.0, "description": "Assessed from JD requirements", "scale": scale})
                break
    if not suggested:
        suggested = [
            {"name": "Technical Skills", "weight": 0.0, "description": "Overall technical alignment with JD", "scale": {"0": "None", "1": "Basic", "2": "Some", "3": "Good", "4": "Strong", "5": "Expert"}},
            {"name": "Experience", "weight": 0.0, "description": "Relevant experience level", "scale": {"0": "None", "1": "<1yr", "2": "1-2yr", "3": "2-4yr", "4": "4-6yr", "5": "6+yr"}},
            {"name": "Culture Fit", "weight": 0.0, "description": "Communication and teamwork", "scale": {"0": "None", "1": "Minimal", "2": "Adequate", "3": "Good", "4": "Strong", "5": "Exceptional"}},
        ]
    total = len(suggested)
    for c in suggested:
        c["weight"] = round(1.0 / total, 2) if total > 0 else 0.2
    remainder = round(1.0 - sum(c["weight"] for c in suggested), 2)
    if suggested and remainder != 0:
        suggested[0]["weight"] = round(suggested[0]["weight"] + remainder, 2)
    return {"criteria": suggested, "evidence_rule": "Every score MUST cite a specific line from the candidate's resume.", "scoring_approach": "Weighted average of 0-5 criterion scores."}


# ─── SESSION STATE ───────────────────────────────────────────────────────────

if "jd" not in st.session_state:
    djd, drub, dcand = load_defaults()
    st.session_state.jd = djd
    st.session_state.rubric = drub
    st.session_state.candidates = dcand
    st.session_state.candidate_names = list(dcand.keys())
    st.session_state.result = None
    st.session_state.ran = False
    st.session_state.trajectory_step = 0
    st.session_state.llm_mode = False
    st.session_state.api_key = os.getenv("OPENAI_API_KEY", "")
    st.session_state.provider = "openai"
    st.session_state.bias_audit_result = None
    st.session_state.is_running = False
    st.session_state.run_start_time = None
    st.session_state.show_config_hint = True

# ─── HEADER ──────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="premium-header animate-fade-in">'
    '<div class="header-content">'
    '<div>'
    '<h1>TechVest Recruitment Agent</h1>'
    '<p class="subtitle">Autonomous candidate scoring, ranking & interview scheduling</p>'
    '<div class="header-badge">'
    '<span class="dot"></span>'
    '<span>LangGraph Engine &nbsp;·&nbsp; '
    f'{"🧠 LLM Mode" if st.session_state.llm_mode else "⚙️ Deterministic Mode"}'
    '</span>'
    '</div>'
    '</div>'
    '<div class="header-actions">'
    '</div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True
)

# ─── GUARDRAIL PILLS ─────────────────────────────────────────────────────────

pills_html = '<div class="pill-container animate-fade-in-delay-1">'
guardrail_pills = [
    ("Step Cap", f"Max {MAX_STEPS} steps", "green"),
    ("Human-in-the-Loop", "Active", "green"),
    ("Injection Defence", "Active", "green"),
    ("Fairness Check", "Active", "green"),
    ("Mode", "LLM" if st.session_state.llm_mode else "Deterministic", "blue" if st.session_state.llm_mode else "purple"),
]
for label, desc, color in guardrail_pills:
    pills_html += f'<span class="pill"><span class="glow-orb {color}"></span>{label}: {desc}</span>'
pills_html += "</div>"
st.markdown(pills_html, unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="padding:0.5rem 0 0.5rem">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem">'
        '<div style="width:32px;height:32px;border-radius:10px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;font-size:1.1rem">⚙️</div>'
        '<div><div style="font-weight:700;font-size:0.95rem;color:#1a1a2e">Configuration</div>'
        '<div style="font-size:0.7rem;color:var(--color-text-secondary)">Agent settings & controls</div></div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )
    
    st.markdown("### Mode")
    
    prev_mode = st.session_state.llm_mode
    st.session_state.llm_mode = st.toggle(
        "🧠 LLM Mode (ReAct Agent)",
        value=st.session_state.llm_mode,
        help="Enable GPT-4o-mini / Claude to decide tool calls autonomously"
    )
    
    if st.session_state.llm_mode:
        with st.container():
            st.markdown(
                '<div style="background:#eef2ff;border-radius:12px;padding:14px;margin:12px 0;border:1px solid rgba(99,102,241,0.2)">'
                '<div style="display:flex;align-items:center;gap:8px">'
                '<span style="font-size:0.8rem;color:#4338ca;font-weight:500">🔑 LLM Mode requires an API key</span>'
                '</div>'
                '</div>',
                unsafe_allow_html=True
            )
        st.session_state.api_key = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.api_key,
            help="OpenAI / OpenRouter / Google API key",
            placeholder="sk-..."
        )
        st.session_state.provider = st.selectbox(
            "Provider",
            ["openai", "openrouter", "google", "github"],
            index=["openai", "openrouter", "google", "github"].index(st.session_state.provider) if st.session_state.provider in ["openai", "openrouter", "google", "github"] else 0,
        )
    
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### Actions")
    
    djd, drub, dcand = load_defaults()
    
    col_reset, col_run = st.columns([1, 1])
    with col_reset:
        if st.button("↺ Reset", use_container_width=True, type="secondary"):
            st.session_state.jd = djd
            st.session_state.rubric = drub
            st.session_state.candidates = dcand
            st.session_state.candidate_names = list(dcand.keys())
            st.session_state.result = None
            st.session_state.ran = False
            st.session_state.trajectory_step = 0
            st.session_state.bias_audit_result = None
            st.session_state.is_running = False
            st.rerun()
    
    with col_run:
        run_btn = st.button(
            "▶ Run Agent",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.is_running,
        )
    
    if st.session_state.get("ran") and st.session_state.result:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### Trajectory Stepper")
        trajectory = st.session_state.result.get("trajectory", [])
        if trajectory:
            max_step = len(trajectory)
            current = st.session_state.trajectory_step
            
            st.markdown(
                f'<div class="step-nav-container">'
                f'<div class="step-indicator">Step {current + 1} of {max_step}</div>'
                f'<div style="margin-top:8px">'
                f'<div class="score-bar-track" style="height:4px">'
                f'<div class="score-bar-fill high" style="width:{(current+1)/max_step*100}%;height:4px"></div>'
                f'</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            
            col_p, col_n = st.columns(2)
            with col_p:
                if st.button("◀ Prev", use_container_width=True, disabled=current <= 0):
                    st.session_state.trajectory_step = current - 1
                    st.rerun()
            with col_n:
                if st.button("Next ▶", use_container_width=True, disabled=current >= max_step - 1):
                    st.session_state.trajectory_step = current + 1
                    st.rerun()
            
            if max_step > 0:
                idx = min(current, max_step - 1)
                step = trajectory[idx]
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#f8f9fc,#ffffff);border-radius:12px;padding:14px;margin-top:10px;border:1px solid #eef0f4">'
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
                    f'<span style="font-size:0.7rem;font-weight:700;color:#6366f1;text-transform:uppercase;letter-spacing:0.5px;background:#eef2ff;padding:2px 10px;border-radius:6px">{step.action}</span>'
                    f'</div>'
                    f'<div style="font-size:0.8rem;color:#475569;margin-bottom:6px;line-height:1.4">{step.thought[:120]}</div>'
                    f'<div style="font-size:0.72rem;color:var(--color-text-secondary);font-family:JetBrains Mono, monospace;background:var(--color-bg-muted);padding:8px;border-radius:8px;border:1px solid var(--color-border-soft)">{step.observation[:120]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("### Fairness Audit")
        if st.button("Run Name-Swap Test", use_container_width=True, type="secondary"):
            profiles = st.session_state.result.get("parsed_profiles", {})
            scorecards = st.session_state.result.get("scorecards", {})
            names = list(profiles.keys())
            if len(names) >= 2:
                swapped = []
                for i in range(len(names)):
                    for j in range(i + 1, len(names)):
                        na, nb = names[i], names[j]
                        if na in scorecards and nb in scorecards:
                            fcheck = fairness_check(profiles[na], profiles[nb], scorecards[na], scorecards[nb])
                            swapped.append(fcheck)
                st.session_state.bias_audit_result = swapped
                st.rerun()

# ─── MAIN TABS ───────────────────────────────────────────────────────────────

config_tab1, config_tab2, config_tab3 = st.tabs([
    ":material/description: Job Description",
    ":material/query_stats: Scoring Rubric",
    ":material/groups: Candidates"
])

with config_tab1:
    col1, col2 = st.columns([4, 1])
    with col1:
        jd_file = st.file_uploader(
            "Upload PDF, DOCX, or TXT",
            type=["txt", "pdf", "docx"],
            key="jd_upload",
            label_visibility="collapsed",
        )
        if jd_file:
            st.session_state.jd = extract_text_from_file(jd_file)
            st.rerun()
    with col2:
        st.metric("Characters", f"{len(st.session_state.jd):,}")
    
    jd_text = st.text_area(
        "Job description",
        st.session_state.jd,
        height=280,
        label_visibility="collapsed",
        placeholder="Paste the job description here..."
    )
    if jd_text != st.session_state.jd:
        st.session_state.jd = jd_text

with config_tab2:
    rubric = st.session_state.rubric
    
    col_suggest, col_info = st.columns([1, 2])
    with col_suggest:
        if st.button("✨ Suggest from JD", use_container_width=True):
            suggested = suggest_criteria_from_jd(st.session_state.jd)
            st.session_state.rubric = suggested
            st.rerun()
    with col_info:
        total_weight = sum(c["weight"] for c in rubric["criteria"])
        st.markdown(
            f'<div style="display:flex;gap:16px;align-items:center">'
            f'<span style="font-size:0.9rem;color:#475569">{len(rubric["criteria"])} criteria</span>'
            f'<span style="width:1px;height:16px;background:#e2e8f0"></span>'
            f'<span style="font-size:0.9rem;color:#475569">Total weight: <strong style="color:{"#22c55e" if abs(total_weight-1.0)<0.01 else "#ef4444"}">{total_weight:.2f}</strong></span>'
            f'</div>',
            unsafe_allow_html=True
        )
        if abs(total_weight - 1.0) > 0.01:
            st.warning(f"Weights sum to {total_weight:.2f}. Adjust sliders to reach 1.0.")
    
    new_criteria = []
    for i, c in enumerate(rubric["criteria"]):
        with st.expander(
            f"{c['name']}  ·  weight: {c['weight']:.2f}",
            expanded=False,
        ):
            col_a, col_b = st.columns([1, 1])
            with col_a:
                name = st.text_input("Criterion name", c["name"], key=f"c_name_{i}")
                weight = st.slider("Weight", 0.0, 1.0, c["weight"], 0.05, key=f"c_weight_{i}")
            with col_b:
                desc = st.text_input("Short description", c["description"], key=f"c_desc_{i}")
            
            st.markdown("**Scale (0–5)** — one line per level as `level: description`")
            scale_str = st.text_area(
                "Scale levels",
                "\n".join(f"{k}: {v}" for k, v in c["scale"].items()),
                height=120,
                key=f"c_scale_{i}",
                label_visibility="collapsed",
            )
            new_scale = {}
            for line in scale_str.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    new_scale[k.strip()] = v.strip()
            new_criteria.append({"name": name, "weight": weight, "description": desc, "scale": new_scale})
    rubric["criteria"] = new_criteria
    st.session_state.rubric = rubric

with config_tab3:
    names = list(st.session_state.candidates.keys())
    
    if not names:
        st.markdown(
            '<div class="empty-state">'
            '<div class="icon-wrap">👥</div>'
            '<h3>No candidates yet</h3>'
            '<p>Add candidates by uploading resumes or pasting text below.</p>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        cand_tabs = st.tabs([f":material/person: {n.split()[0]}" for n in names] + [":material/add_circle: Add"])
        
        for idx, name in enumerate(names):
            with cand_tabs[idx]:
                c1, c2 = st.columns([1, 5])
                with c1:
                    cand_file = st.file_uploader(
                        "Upload", type=["txt", "pdf", "docx"],
                        key=f"upd_{name}", label_visibility="collapsed"
                    )
                    if cand_file:
                        st.session_state.candidates[name] = extract_text_from_file(cand_file)
                        st.rerun()
                    if st.button(f"🗑 Remove", key=f"rm_{name}", use_container_width=True):
                        del st.session_state.candidates[name]
                        st.session_state.candidate_names = list(st.session_state.candidates.keys())
                        st.rerun()
                with c2:
                    resume_text = st.text_area(
                        "Resume text",
                        st.session_state.candidates[name],
                        height=260,
                        key=f"resume_{name}",
                        label_visibility="collapsed",
                    )
                    if resume_text != st.session_state.candidates[name]:
                        st.session_state.candidates[name] = resume_text
        
        with cand_tabs[-1]:
            nc1, nc2 = st.columns(2)
            with nc1:
                new_file = st.file_uploader(
                    "Upload resume (PDF, DOCX, TXT)",
                    type=["txt", "pdf", "docx"],
                    key="new_cand_file",
                )
                new_name = st.text_input("Candidate name", key="new_cand_name", placeholder="e.g. Alex Kumar")
                if new_file and new_name:
                    extracted = extract_text_from_file(new_file)
                    st.session_state.candidates[new_name] = extracted
                    st.session_state.candidate_names = list(st.session_state.candidates.keys())
                    st.rerun()
            with nc2:
                new_resume = st.text_area("Or paste resume text", height=140, key="new_cand_resume", placeholder="Paste the full resume text here...")
                new_name2 = st.text_input("Candidate name", key="new_cand_name2", placeholder="e.g. Alex Kumar")
                if st.button("➕ Add Candidate", use_container_width=True) and new_name2 and new_resume:
                    st.session_state.candidates[new_name2] = new_resume
                    st.session_state.candidate_names = list(st.session_state.candidates.keys())
                    st.rerun()

# ─── DIVIDER ─────────────────────────────────────────────────────────────────

st.markdown('<hr style="margin:1.2rem 0">', unsafe_allow_html=True)

# ─── RUN AGENT ───────────────────────────────────────────────────────────────

if run_btn:
    candidates = st.session_state.candidates
    if not candidates:
        st.error("Add at least one candidate before running.")
    else:
        if st.session_state.llm_mode and not st.session_state.api_key:
            st.error("API key required for LLM mode. Enter it in the sidebar or switch to deterministic mode.")
        else:
            st.session_state.is_running = True
            st.session_state.run_start_time = datetime.now()
            
            # Show premium animated loading state
            with st.container():
                st.markdown(
                    '<div class="glass-card animate-scale-in" style="text-align:center;padding:3rem 2rem">'
                    '<div class="loading-container">'
                    '<div class="loading-spinner"></div>'
                    '<h3 style="color:#1a1a2e;font-weight:600;margin-bottom:0.5rem;font-size:1.3rem">Agent is processing</h3>'
                    '<p style="color:var(--color-text-secondary);font-size:0.9rem;margin-bottom:0.3rem">Parsing resumes · Scoring candidates · Building shortlist</p>'
                    '<div style="max-width:420px;margin:1.8rem auto 0;width:100%">'
                    '<div class="score-bar-track" style="height:6px">'
                    '<div class="score-bar-fill high" style="width:0%;height:6px;animation:progress-fill 2.5s ease-out forwards"></div>'
                    '</div>'
                    '<div style="display:flex;justify-content:space-between;margin-top:8px">'
                    '<span style="font-size:0.7rem;color:var(--color-text-muted);font-weight:500">Parsing</span>'
                    '<span style="font-size:0.7rem;color:var(--color-text-muted);font-weight:500">Scoring</span>'
                    '<span style="font-size:0.7rem;color:var(--color-text-muted);font-weight:500">Ranking</span>'
                    '<span style="font-size:0.7rem;color:var(--color-text-muted);font-weight:500">Done</span>'
                    '</div>'
                    '</div>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True
                )
            
            # Run the agent
            try:
                app = build_graph()
                initial_state = {
                    "job_description": st.session_state.jd,
                    "rubric": st.session_state.rubric,
                    "candidates": candidates,
                    "parsed_profiles": {},
                    "scorecards": {},
                    "shortlist": [],
                    "trajectory": [],
                    "current_candidate": None,
                    "candidates_remaining": list(candidates.keys()),
                    "phase": "planning",
                    "step_count": 0,
                    "human_approval_pending": None,
                    "injection_attempt_detected": False,
                    "fairness_checked": False,
                    "error": None,
                    "messages": [],
                    "llm_mode": st.session_state.llm_mode,
                    "api_key": st.session_state.api_key if st.session_state.llm_mode else "",
                    "provider": st.session_state.provider if st.session_state.llm_mode else "",
                }
                config = {"recursion_limit": MAX_STEPS, "configurable": {"thread_id": "recruitment-1"}}
                result = app.invoke(initial_state, config=config)
                st.session_state.result = result
                st.session_state.ran = True
                st.session_state.trajectory_step = 0
                st.session_state.bias_audit_result = None
                st.session_state.is_running = False
                st.rerun()
            except Exception as e:
                st.error(f"Agent run failed: {e}")
                st.session_state.is_running = False
                st.session_state.ran = False

# ─── RESULTS ─────────────────────────────────────────────────────────────────

if st.session_state.get("ran") and st.session_state.result:
    result = st.session_state.result
    shortlist = result.get("shortlist", [])
    trajectory = result.get("trajectory", [])
    step_count = result.get("step_count", 0)
    inj = result.get("injection_attempt_detected", False)
    
    # ── Stats Bar ──
    interview_count = sum(1 for e in shortlist if e.recommendation == "interview")
    hold_count = sum(1 for e in shortlist if e.recommendation == "hold")
    reject_count = sum(1 for e in shortlist if e.recommendation == "reject")
    pending = [e for e in shortlist if e.proposed_action and e.proposed_action.status == "pending_approval"]
    
    st.markdown(
        f'<div class="glass-card animate-fade-in" style="margin-bottom:1.5rem;padding:1.5rem 1.5rem">'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:14px">'
        f'<div class="metric-card metric-default"><div class="label">Candidates</div><div class="value" style="color:#6366f1">{len(shortlist)}</div></div>'
        f'<div class="metric-card metric-interview"><div class="label">Interview</div><div class="value" style="color:#22c55e">{interview_count}</div></div>'
        f'<div class="metric-card metric-hold"><div class="label">Hold</div><div class="value" style="color:#f59e0b">{hold_count}</div></div>'
        f'<div class="metric-card metric-reject"><div class="label">Reject</div><div class="value" style="color:#ef4444">{reject_count}</div></div>'
        f'<div class="metric-card metric-default"><div class="label">Steps</div><div class="value" style="color:{"#ef4444" if step_count>=MAX_STEPS else "#475569"}">{step_count}</div></div>'
        f'<div class="metric-card metric-default"><div class="label">Injection</div><div class="value" style="color:{"#ef4444" if inj else "#22c55e"}">{"⚠" if inj else "✓"}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True
    )
    
    res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs([
        ":material/trophy: Shortlist",
        ":material/account_tree: Trajectory",
        ":material/security: Guardrails",
        ":material/balance: Fairness",
    ])
    
    # ── TAB 1: SHORTLIST ──
    with res_tab1:
        if not shortlist:
            st.markdown(
                '<div class="empty-state">'
                '<div class="icon-wrap">📋</div>'
                '<h3>No shortlist produced</h3>'
                '<p>The agent did not produce any results. Check the configuration and try again.</p>'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            for idx, entry in enumerate(shortlist):
                score = entry.scorecard.weighted_total
                score_class = "high" if score >= 3.5 else ("mid" if score >= 2.0 else "low")
                badge_class = entry.recommendation
                
                # Calculate circumference for SVG ring
                circumference = 2 * 3.14159 * 28
                offset = circumference * (1 - score / 5.0)
                
                # Get avatar initial
                initial = entry.candidate_name[0].upper() if entry.candidate_name else "?"
                
                st.markdown(
                    f'<div class="premium-card animate-fade-in" style="animation-delay:{idx * 0.1}s;margin-bottom:1rem">'
                    f'<div class="accent-bar {badge_class}"></div>'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;padding-top:4px">'
                    f'<div style="display:flex;align-items:center;gap:16px">'
                    f'<div class="candidate-avatar {badge_class}">#{entry.rank}</div>'
                    f'<div>'
                    f'<div style="font-size:1.1rem;font-weight:600;color:#1a1a2e;display:flex;align-items:center;gap:10px">'
                    f'{entry.candidate_name}'
                    f'<span class="verdict-badge {badge_class}">'
                    f'{"✅" if badge_class=="interview" else "⏸️" if badge_class=="hold" else "❌"} {entry.recommendation.upper()}'
                    f'</span>'
                    f'</div>'
                    f'<div style="font-size:0.78rem;color:var(--color-text-secondary);margin-top:4px">{entry.justification[:80]}{"..." if len(entry.justification) > 80 else ""}</div>'
                    f'</div>'
                    f'</div>'
                    f'<div class="score-ring-container">'
                    f'<svg class="score-ring-svg" viewBox="0 0 72 72">'
                    f'<circle class="score-ring-bg" cx="36" cy="36" r="28"/>'
                    f'<circle class="score-ring-fill {score_class}" cx="36" cy="36" r="28" '
                    f'stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"/>'
                    f'</svg>'
                    f'<div class="score-ring-text">{score:.1f}</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                # Interview proposal
                if entry.proposed_action:
                    slot = entry.proposed_action.slot
                    status = entry.proposed_action.status
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(
                            f'<div class="interview-proposal">'
                            f'<div style="display:flex;align-items:center;gap:10px">'
                            f'<span style="font-size:1.3rem">📅</span>'
                            f'<div>'
                            f'<div style="font-weight:600;font-size:0.9rem;color:#1a1a2e">Interview Proposed</div>'
                            f'<div style="color:#475569;font-size:0.85rem;margin-top:2px">{slot.date} @ {slot.time} ({slot.duration_minutes}min)</div>'
                            f'</div>'
                            f'</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    with col_b:
                        if status == "pending_approval":
                            if st.button(f"✓ Approve", key=f"app_{entry.candidate_name}", use_container_width=True):
                                entry.proposed_action.status = "approved"
                                st.success("Interview approved!")
                                st.rerun()
                        else:
                            st.markdown(
                                f'<div style="background:#dcfce7;border-radius:10px;padding:10px 14px;text-align:center;margin-top:8px;border:1px solid #86efac">'
                                f'<span style="font-size:0.8rem;font-weight:600;color:#166534">✓ Approved</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                
                # Scorecard expander
                with st.expander("Scorecard & Evidence", expanded=False):
                    for cs in entry.scorecard.criterion_scores:
                        bar_width = (cs.score / 5.0) * 100
                        bar_color = "#22c55e" if cs.score >= 4 else "#f59e0b" if cs.score >= 2 else "#ef4444"
                        bar_class = "high" if cs.score >= 4 else "mid" if cs.score >= 2 else "low"
                        st.markdown(
                            f'<div style="margin-bottom:14px">'
                            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
                            f'<span style="font-size:0.85rem;font-weight:500;color:#1a1a2e">{cs.criterion}</span>'
                            f'<span style="font-size:0.85rem;font-weight:700;color:{bar_color}">{cs.score}/5 <span style="font-weight:400;color:var(--color-text-muted)">(w: {cs.weight})</span></span>'
                            f'</div>'
                            f'<div class="score-bar-track">'
                            f'<div class="score-bar-fill {bar_class}" style="width:{bar_width}%"></div>'
                            f'</div>'
                            f'<div style="font-size:0.75rem;color:var(--color-text-secondary);margin-top:6px;font-style:italic;display:flex;align-items:center;gap:4px">'
                            f'📎 {cs.evidence[:100]}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
    
    # ── TAB 2: TRAJECTORY ──
    with res_tab2:
        if not trajectory:
            st.markdown(
                '<div class="empty-state">'
                '<div class="icon-wrap">🔍</div>'
                '<h3>No trajectory recorded</h3>'
                '<p>The agent did not log any reasoning steps. This may indicate an issue with the run.</p>'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="margin-bottom:1rem;display:flex;align-items:center;gap:8px">'
                f'<span style="font-size:0.85rem;color:var(--color-text-secondary);background:var(--color-bg-card);padding:6px 14px;border-radius:8px;border:1px solid var(--color-border)">Showing {len(trajectory)} reasoning steps</span>'
                '</div>',
                unsafe_allow_html=True
            )
            
            for i, step in enumerate(trajectory):
                is_last = i == len(trajectory) - 1
                st.markdown(
                    f'<div class="traj-step {"active" if is_last else ""}" style="animation:fadeInUp 0.3s ease-out {i*0.05}s both">'
                    f'<div class="step-number">Step {step.step_number}</div>'
                    f'<div class="step-content">'
                    f'<div class="step-action">{step.action}</div>'
                    f'<div class="step-thought">{step.thought[:150]}</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            
            with st.expander("Full Audit Log (JSON)", expanded=False):
                st.code(
                    json.dumps([s.model_dump() for s in trajectory], indent=2),
                    language="json",
                )
    
    # ── TAB 3: GUARDRAILS ──
    with res_tab3:
        st.markdown(
            '<div style="margin-bottom:1rem">'
            '<h4 style="font-weight:600;color:#1a1a2e">Safety & compliance overview</h4>'
            '<p style="font-size:0.85rem;color:var(--color-text-secondary)">All guardrail systems active during this agent run.</p>'
            '</div>',
            unsafe_allow_html=True
        )
        
        guardrail_data = [
            ("🔄", "Step Cap", f"{step_count}/{MAX_STEPS}", "green" if step_count < MAX_STEPS else "red",
             f"The agent used {step_count} of {MAX_STEPS} allowed steps."),
            ("🛡️", "Injection Defence", "Blocked" if inj else "Clear", "red" if inj else "green",
             "Prompt injection attempt was detected and blocked." if inj else "No injection attempts detected."),
            ("👤", "Human-in-the-Loop", f"{len(pending)} pending", "amber" if pending else "green",
             f"{len(pending)} interview(s) awaiting human approval."),
            ("⚖️", "Fairness Check", "Active", "green",
             "Name-blind scoring on JD-relevant criteria only."),
            ("🧠", "Mode", "LLM" if st.session_state.llm_mode else "Deterministic", "blue" if st.session_state.llm_mode else "purple",
             "GPT-4o-mini decides tool calls" if st.session_state.llm_mode else "Rule-based deterministic engine."),
            ("📝", "Audit Log", f"{len(trajectory)} steps", "green",
             "Full trajectory persisted for decision reconstruction."),
        ]
        
        cols = st.columns(3)
        for i, (icon, title, value, color, desc) in enumerate(guardrail_data):
            text_color = "#22c55e" if color == "green" else "#f59e0b" if color == "amber" else "#ef4444" if color == "red" else "#6366f1" if color == "blue" else "#8b5cf6"
            with cols[i % 3]:
                st.markdown(
                    f'<div class="guardrail-card" style="animation-delay:{i * 0.08}s">'
                    f'<div class="guardrail-icon">{icon}</div>'
                    f'<div class="guardrail-title">{title}</div>'
                    f'<div class="guardrail-value" style="color:{text_color}">{value}</div>'
                    f'<div class="guardrail-desc">{desc}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        
        if inj:
            st.error("⚠️ Prompt injection attempt detected and blocked. A resume contained instructions attempting to override the scoring system. The agent correctly ignored them.")
        
        if pending:
            st.info(f"👤 {len(pending)} interview(s) pending human approval. Go to the Shortlist tab to review and approve.")
    
    # ── TAB 4: FAIRNESS ──
    with res_tab4:
        profiles = result.get("parsed_profiles", {})
        scorecards = result.get("scorecards", {})
        names = list(profiles.keys())
        
        if len(names) >= 2:
            st.markdown(
                '<div class="glass-card animate-fade-in" style="margin-bottom:1.5rem">'
                '<h4 style="font-weight:600;margin-bottom:0.3rem">⚖️ Pairwise Fairness Comparison</h4>'
                '<p style="font-size:0.85rem;color:var(--color-text-secondary)">Comparing scores on JD-relevant criteria only (name, gender, age, and college are excluded).</p>'
                '</div>',
                unsafe_allow_html=True
            )
            
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    na, nb = names[i], names[j]
                    if na in profiles and nb in profiles and na in scorecards and nb in scorecards:
                        fcheck = fairness_check(profiles[na], profiles[nb], scorecards[na], scorecards[nb])
                        
                        passed = fcheck["passed"]
                        st.markdown(
                            f'<div class="fairness-card {"passed" if passed else "failed"}">'
                            f'<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">'
                            f'<div style="font-weight:600;font-size:0.95rem;min-width:100px">{na}</div>'
                            f'<div style="text-align:center;background:#ffffff;border-radius:10px;padding:6px 16px;border:1px solid #eef0f4">'
                            f'<div style="font-size:1.3rem;font-weight:700;color:#6366f1">{fcheck["relevant_score_a"]:.2f}</div>'
                            f'</div>'
                            f'<div style="font-size:0.85rem;color:var(--color-text-muted)">vs</div>'
                            f'<div style="font-weight:600;font-size:0.95rem;min-width:100px">{nb}</div>'
                            f'<div style="text-align:center;background:#ffffff;border-radius:10px;padding:6px 16px;border:1px solid #eef0f4">'
                            f'<div style="font-size:1.3rem;font-weight:700;color:#6366f1">{fcheck["relevant_score_b"]:.2f}</div>'
                            f'</div>'
                            f'<span style="padding:5px 14px;border-radius:100px;font-size:0.75rem;font-weight:600;{"background:#dcfce7;color:#166534" if passed else "background:#fce4ec;color:#b71c1c"}">'
                            f'{"✓ Consistent" if passed else "✗ Bias Detected"}'
                            f'</span>'
                            f'</div>'
                            f'<div style="font-size:0.75rem;color:var(--color-text-secondary);margin-top:8px;padding:0 4px">{fcheck["note"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
        
        if st.session_state.bias_audit_result:
            st.markdown(
                '<div class="glass-card animate-fade-in" style="margin-top:1.5rem">'
                '<h4 style="font-weight:600;margin-bottom:0.3rem">📋 Bias Audit Report</h4>'
                '<p style="font-size:0.85rem;color:var(--color-text-secondary)">Name-swap test: candidate names were swapped to check for inconsistent scoring.</p>'
                '</div>',
                unsafe_allow_html=True
            )
            
            for check in st.session_state.bias_audit_result:
                passed = check["passed"]
                st.markdown(
                    f'<div class="fairness-card {"passed" if passed else "failed"}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'
                    f'<div><strong>{check["candidate_a"]}</strong> vs <strong>{check["candidate_b"]}</strong></div>'
                    f'<div style="font-weight:600;font-size:0.9rem;color:{"#166534" if passed else "#b71c1c"}">'
                    f'{"✓ Consistent" if passed else "✗ Inconsistent"}'
                    f'</div>'
                    f'</div>'
                    f'<div style="font-size:0.85rem;color:#475569;margin-top:6px">'
                    f'Scores: {check["relevant_score_a"]:.2f} vs {check["relevant_score_b"]:.2f}'
                    f'</div>'
                    f'<div style="font-size:0.78rem;color:var(--color-text-secondary);margin-top:4px">{check["note"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        
        if len(names) < 2:
            st.markdown(
                '<div class="empty-state">'
                '<div class="icon-wrap">⚖️</div>'
                '<h3>Not enough candidates</h3>'
                '<p>Add at least 2 candidates to run fairness comparisons.</p>'
                '</div>',
                unsafe_allow_html=True
            )

elif not st.session_state.get("ran"):
    # Premium onboarding/empty state
    st.markdown(
        '<div class="empty-state animate-fade-in">'
        '<div class="icon-wrap" style="font-size:4.5rem">🤖</div>'
        '<h3>Ready to evaluate candidates</h3>'
        '<p>Configure the job description, scoring rubric, and candidate resumes, then click <strong>Run Agent</strong> in the sidebar.</p>'
        '<div class="onboarding-flow">'
        '<div class="onboarding-step">'
        '<span class="step-num">1</span>'
        '<span>Set Job Description</span>'
        '</div>'
        '<span class="onboarding-arrow">→</span>'
        '<div class="onboarding-step">'
        '<span class="step-num">2</span>'
        '<span>Configure Rubric</span>'
        '</div>'
        '<span class="onboarding-arrow">→</span>'
        '<div class="onboarding-step">'
        '<span class="step-num">3</span>'
        '<span>Add Candidates</span>'
        '</div>'
        '<span class="onboarding-arrow">→</span>'
        '<div class="onboarding-step active">'
        '<span class="step-num">4</span>'
        '<span>Run Agent</span>'
        '</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )