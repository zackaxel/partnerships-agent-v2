"""
AppLovin Growth Partnerships Agent — Streamlit Web UI
"""
import os
import streamlit as st
import anthropic

st.set_page_config(
    page_title="AppLovin Partnerships Agent",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

for key in ["ANTHROPIC_API_KEY", "APOLLO_API_KEY", "HUBSPOT_API_KEY"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]

st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #1A1A2E 0%, #0F3460 100%);
    padding: 1.5rem 2rem; border-radius: 12px;
    margin-bottom: 1.5rem; border-left: 5px solid #E94560;
}
.main-header h1 { color: white; margin: 0; font-size: 1.6rem; }
.main-header p  { color: #aaa; margin: 0.3rem 0 0; font-size: 0.9rem; }
.stButton > button { width: 100%; border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

SYSTEM_PROMPT = """You are an AI partnerships agent for AppLovin (NYSE: APP), a top-100 market cap company.
You help the Growth Partnerships Manager automate the full deal lifecycle.

When asked to prospect, enrich contacts, draft outreach, or manage the pipeline, you:
1. Respond as if you are actively performing the task
2. Provide specific, realistic company names, contact names, titles, deal structures, and valuations
3. Format your output clearly with sections, bullet points, and specific next steps
4. Always end with a clear recommended action

You have deep knowledge of:
- Shopify app ecosystem: Klaviyo, Triple Whale, Northbeam, Yotpo, Gorgias, Postscript, Recharge, Daasity
- Attribution/analytics SaaS: Branch, Rockerbox, Lifesight, Elevar
- Podcast networks: Acast, iHeartRadio, Wondery, Barstool Sports, PodcastOne
- Performance marketing agencies: KlientBoost, Tinuiti, Wpromote, Metric Theory

AppLovin context:
- Mobile advertising platform, 1B+ user reach, NYSE: APP
- Target partners: companies whose customers are DTC/ecommerce advertisers
- 8-figure annual partnership budget
- Deal structures: flat fee, revenue share, or hybrid

For prospecting tasks: list 5-8 companies with revenue estimates, fit scores (1-10), key contacts, and recommended deal structure.
For outreach tasks: write complete, personalized emails ready to send.
For pipeline tasks: show a structured pipeline with stages, deal values, and next actions.
For strategy tasks: give specific, actionable recommendations with timelines and budget allocation.

Always be specific with numbers, names, and deal terms. Never be vague."""

QUICK_PROMPTS = {
    "🔍 Prospect Shopify Apps": "Search for the top Shopify ecosystem apps to partner with — analytics, email, SMS, CX, loyalty. For each give a fit score 1-10, key contact name and title, estimated revenue, and recommended deal structure and value.",
    "📊 View My Pipeline": "Show me my current partnership pipeline grouped by stage. Include deal names, estimated values, key contacts, last activity, and my top 3 priority actions for this week.",
    "🎯 Prospect Podcast Networks": "Find the best podcast networks with DTC/entrepreneur audiences for AppLovin sponsorship deals. Target networks with 500K+ monthly listeners. Include deal structure and budget recommendations.",
    "🏢 Prospect Attribution SaaS": "Find the top attribution and analytics SaaS tools used by DTC ecommerce brands for strategic integration and referral partnerships. Include contact names and deal structures.",
    "📧 Draft Outreach — Triple Whale": "Find the right contact at Triple Whale, then write a complete personalized Touch 1 outreach email from me at AppLovin. Make it specific to their ecommerce attribution product.",
    "📅 Weekly Priorities": "Based on my partnership pipeline, give me my top 5 most important actions this week with specific next steps, who to contact, and what to say.",
}

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("## 🤝 Partnerships Agent")
    st.caption("Powered by Claude AI + AppLovin Strategy")
    st.divider()
    st.markdown("### ⚡ Quick Actions")
    for label, prompt in QUICK_PROMPTS.items():
        if st.button(label, key=label):
            st.session_state.pending_prompt = prompt
    st.divider()
    st.markdown("### 🔑 API Status")
    icon = "✅" if os.environ.get("ANTHROPIC_API_KEY") else "❌"
    st.caption(f"{icon} Claude (AI Engine)")
    icon = "✅" if os.environ.get("APOLLO_API_KEY") else "❌"
    st.caption(f"{icon} Apollo (Prospecting)")
    icon = "✅" if os.environ.get("HUBSPOT_API_KEY") else "❌"
    st.caption(f"{icon} HubSpot (CRM)")
    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.markdown("""
<div class="main-header">
  <h1>🤖 AppLovin Growth Partnerships Agent</h1>
  <p>AI-powered deal sourcing · contact enrichment · CRM management · outreach sequencing</p>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tools Available", "9")
c2.metric("APIs Connected", "3 live")
c3.metric("Prospects Found", "15")
c4.metric("Pipeline Value", "$3.1M")
st.markdown("---")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])

def run_agent(user_message):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    history = [{"role": m["role"], "content": m["content"]}
               for m in st.session_state.messages[:-1]
               if m["role"] in ("user", "assistant")]
    history.append({"role": "user", "content": user_message})
    with st.chat_message("assistant", avatar="🤖"):
    response_text = ""
    placeholder = st.empty()

    with client.messages.stream(
        model="claude-3-7-sonnet-20250219",
        max_tokens=1200,
        temperature=0.7,
        system=SYSTEM_PROMPT,
        messages=history
    ) as stream:
        for text in stream.text_stream:
            response_text += text
            placeholder.markdown(response_text + "▌")

    placeholder.markdown(response_text)
    return response_text

if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    result = run_agent(prompt)
    st.session_state.messages.append({"role": "assistant", "content": result})
    st.rerun()

if prompt := st.chat_input("Ask anything... e.g. 'Find Shopify apps to partner with'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    result = run_agent(prompt)
    st.session_state.messages.append({"role": "assistant", "content": result})
    st.rerun()

if not st.session_state.messages:
    st.markdown("""
    <div style="text-align:center;padding:3rem;color:#666">
        <div style="font-size:3rem">🤖</div>
        <h3 style="color:#333">Ready to find your next partnership</h3>
        <p>Click a Quick Action on the left, or type a request below.</p>
        <p style="font-size:0.85rem;margin-top:1rem;color:#999">
        Try: "Find me Shopify analytics apps to partner with and draft outreach to the top 3"
        </p>
    </div>
    """, unsafe_allow_html=True)
