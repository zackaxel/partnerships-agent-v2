"""
AppLovin Growth Partnerships Agent
====================================
Single-file Streamlit app — no subfolders, no import issues.
Deploy to Streamlit Cloud → share the URL.
"""

import os, json
import streamlit as st
import anthropic
import requests

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AppLovin Partnerships Agent",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load secrets ──────────────────────────────────────────────────────────────
for key in ["ANTHROPIC_API_KEY", "APOLLO_API_KEY", "HUBSPOT_API_KEY"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #1A1A2E 0%, #0F3460 100%);
    padding: 1.5rem 2rem; border-radius: 12px;
    margin-bottom: 1.5rem; border-left: 5px solid #E94560;
}
.main-header h1 { color: white; margin: 0; font-size: 1.6rem; }
.main-header p  { color: #aaa; margin: 0.3rem 0 0; font-size: 0.9rem; }
.tool-call {
    background: #1e2a3a; border-left: 3px solid #E94560;
    padding: 0.6rem 1rem; border-radius: 0 8px 8px 0;
    margin: 0.4rem 0; font-family: monospace; font-size: 0.82rem; color: #ccc;
}
.tool-result {
    background: #0d1f0d; border-left: 3px solid #27AE60;
    padding: 0.6rem 1rem; border-radius: 0 8px 8px 0;
    margin: 0.4rem 0 0.8rem; font-family: monospace; font-size: 0.82rem; color: #9ef09e;
}
.stButton > button { width: 100%; border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# APOLLO TOOLS
# ════════════════════════════════════════════════════════════════════════════

APOLLO_BASE = "https://api.apollo.io/api/v1"

def apollo_headers():
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": os.environ.get("APOLLO_API_KEY", ""),
    }

def apollo_search_companies(keywords=None, employee_ranges=None, domains=None, limit=10):
    payload = {"per_page": min(limit, 25)}
    if keywords:
        payload["q_organization_keyword_tags"] = keywords
    if employee_ranges:
        payload["organization_num_employees_ranges"] = employee_ranges
    if domains:
        payload["q_organization_domains_list"] = domains
    try:
        r = requests.post(f"{APOLLO_BASE}/mixed_companies/search", headers=apollo_headers(), json=payload)
        r.raise_for_status()
        orgs = r.json().get("organizations", [])
        if not orgs:
            return "No companies found matching those criteria."
        lines = []
        for o in orgs:
            rev = o.get("organization_revenue_printed", "N/A")
            g = o.get("organization_headcount_twenty_four_month_growth")
            g_str = f"{g:+.0%}" if g is not None else "N/A"
            lines.append(f"• {o['name']} | {o.get('primary_domain','N/A')} | Revenue: ${rev} | HC Growth 24mo: {g_str} | ID: {o['id']}")
        return f"Found {len(orgs)} companies:\n" + "\n".join(lines)
    except Exception as e:
        return f"Apollo error: {str(e)}"

def apollo_search_contacts(domains, titles=None, seniorities=None, limit=5):
    payload = {
        "per_page": limit,
        "q_organization_domains_list": domains,
        "person_seniorities": seniorities or ["vp", "director", "c_suite", "owner"],
    }
    if titles:
        payload["person_titles"] = titles
    try:
        r = requests.post(f"{APOLLO_BASE}/mixed_people/search", headers=apollo_headers(), json=payload)
        r.raise_for_status()
        people = r.json().get("people", [])
        if not people:
            return "No contacts found."
        lines = []
        for p in people:
            email = "✓ email" if p.get("has_email") else "✗ email"
            phone = "✓ phone" if p.get("has_direct_phone") == "Yes" else "✗ phone"
            lines.append(f"• {p['first_name']} {p.get('last_name_obfuscated','?')} — {p.get('title','N/A')} @ {p.get('organization',{}).get('name','N/A')} | {email}, {phone} | ID: {p['id']}")
        return f"Found {len(people)} contacts:\n" + "\n".join(lines)
    except Exception as e:
        return f"Apollo error: {str(e)}"

def apollo_enrich_contact(first_name, domain, last_name=None, linkedin_url=None):
    payload = {"first_name": first_name, "domain": domain}
    if last_name:
        payload["last_name"] = last_name
    if linkedin_url:
        payload["linkedin_url"] = linkedin_url
    try:
        r = requests.post(f"{APOLLO_BASE}/people/match", headers=apollo_headers(), json=payload)
        r.raise_for_status()
        p = r.json().get("person", {})
        if not p:
            return "No match found."
        return (f"Enriched contact:\n"
                f"  Name: {p.get('first_name','')} {p.get('last_name','')}\n"
                f"  Title: {p.get('title','N/A')}\n"
                f"  Email: {p.get('email','Not available')}\n"
                f"  Phone: {p.get('direct_phone', p.get('sanitized_phone','Not available'))}\n"
                f"  LinkedIn: {p.get('linkedin_url','N/A')}\n"
                f"  ID: {p.get('id','N/A')}")
    except Exception as e:
        return f"Apollo error: {str(e)}"

def apollo_get_campaigns():
    try:
        r = requests.post(f"{APOLLO_BASE}/emailer_campaigns/search", headers=apollo_headers(), json={})
        r.raise_for_status()
        campaigns = r.json().get("emailer_campaigns", [])
        if not campaigns:
            return "No email campaigns found. Create sequences in Apollo first."
        lines = [f"• [{c['id']}] {c.get('name','Unnamed')} — Active: {c.get('active','N/A')}" for c in campaigns[:20]]
        return f"{len(campaigns)} campaigns:\n" + "\n".join(lines)
    except Exception as e:
        return f"Apollo error: {str(e)}"

def apollo_enroll_sequence(contact_ids, campaign_id):
    try:
        r = requests.post(
            f"{APOLLO_BASE}/emailer_campaigns/{campaign_id}/add_contact_ids",
            headers=apollo_headers(),
            json={"contact_ids": contact_ids, "campaign_id": campaign_id},
        )
        r.raise_for_status()
        return f"✓ Enrolled {len(contact_ids)} contact(s) in campaign {campaign_id}."
    except Exception as e:
        return f"Apollo error: {str(e)}"

# ════════════════════════════════════════════════════════════════════════════
# HUBSPOT TOOLS
# ════════════════════════════════════════════════════════════════════════════

HUBSPOT_BASE = "https://api.hubapi.com"

def hs_headers():
    return {
        "Authorization": f"Bearer {os.environ.get('HUBSPOT_API_KEY', '')}",
        "Content-Type": "application/json",
    }

def hubspot_create_deal(company_name, deal_name, stage, amount=None, deal_type=None, notes=None):
    props = {"dealname": deal_name, "dealstage": stage, "pipeline": "default"}
    if amount:
        props["amount"] = str(amount)
    if deal_type:
        props["dealtype"] = deal_type
    if notes:
        props["description"] = notes
    try:
        r = requests.post(f"{HUBSPOT_BASE}/crm/v3/objects/deals", headers=hs_headers(), json={"properties": props})
        r.raise_for_status()
        deal_id = r.json()["id"]
        return f"✓ Deal created in HubSpot (ID: {deal_id}): {deal_name} | Stage: {stage} | Value: ${amount:,}" if amount else f"✓ Deal created (ID: {deal_id}): {deal_name}"
    except Exception as e:
        return f"HubSpot error: {str(e)}"

def hubspot_update_deal(deal_id, stage=None, amount=None, notes=None):
    props = {}
    if stage:
        props["dealstage"] = stage
    if amount:
        props["amount"] = str(amount)
    if notes:
        props["description"] = notes
    if not props:
        return "No updates provided."
    try:
        r = requests.patch(f"{HUBSPOT_BASE}/crm/v3/objects/deals/{deal_id}", headers=hs_headers(), json={"properties": props})
        r.raise_for_status()
        return f"✓ Deal {deal_id} updated: {props}"
    except Exception as e:
        return f"HubSpot error: {str(e)}"

def hubspot_get_pipeline(stage_filter=None):
    body = {
        "filterGroups": [],
        "properties": ["dealname", "dealstage", "amount", "hs_lastmodifieddate"],
        "limit": 50,
    }
    if stage_filter:
        body["filterGroups"] = [{"filters": [{"propertyName": "dealstage", "operator": "EQ", "value": stage_filter}]}]
    try:
        r = requests.post(f"{HUBSPOT_BASE}/crm/v3/objects/deals/search", headers=hs_headers(), json=body)
        r.raise_for_status()
        deals = r.json().get("results", [])
        if not deals:
            return "No deals found in pipeline."
        stage_map = {
            "appointmentscheduled": "Prospected", "qualifiedtobuy": "Contacted",
            "presentationscheduled": "In Talks", "decisionmakerboughtin": "Term Sheet",
            "closedwon": "Closed Won", "closedlost": "Closed Lost",
        }
        total = 0
        lines = []
        for d in deals:
            p = d.get("properties", {})
            stage = stage_map.get(p.get("dealstage", ""), p.get("dealstage", "Unknown"))
            amt = p.get("amount")
            amt_str = f"${float(amt):,.0f}" if amt else "TBD"
            if amt:
                total += float(amt)
            lines.append(f"  [{stage}] {p.get('dealname','N/A')} — {amt_str}")
        return f"Pipeline: {len(deals)} deals | Total Est. Value: ${total:,.0f}\n" + "\n".join(lines)
    except Exception as e:
        return f"HubSpot error: {str(e)}"

def hubspot_create_contact(first_name, last_name, email, company=None, job_title=None, phone=None):
    props = {"firstname": first_name, "lastname": last_name, "email": email}
    if company:
        props["company"] = company
    if job_title:
        props["jobtitle"] = job_title
    if phone:
        props["phone"] = phone
    try:
        r = requests.post(f"{HUBSPOT_BASE}/crm/v3/objects/contacts", headers=hs_headers(), json={"properties": props})
        r.raise_for_status()
        return f"✓ Contact created (ID: {r.json()['id']}): {first_name} {last_name} at {company or 'N/A'}"
    except Exception as e:
        return f"HubSpot error: {str(e)}"

# ════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (passed to Claude)
# ════════════════════════════════════════════════════════════════════════════

ALL_TOOLS = [
    {
        "name": "apollo_search_companies",
        "description": "Search Apollo.io for companies matching partnership criteria (Shopify apps, analytics SaaS, podcast networks, agencies). Returns revenue, headcount, growth signals.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keyword tags e.g. ['shopify app', 'ecommerce analytics']"},
                "employee_ranges": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['11,50', '51,200', '201,500']"},
                "domains": {"type": "array", "items": {"type": "string"}, "description": "Specific domains e.g. ['triplewhale.com']"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "apollo_search_contacts",
        "description": "Find decision-makers at a company on Apollo (VP/Director of Partnerships, BD, CRO, CEO).",
        "input_schema": {
            "type": "object",
            "properties": {
                "domains": {"type": "array", "items": {"type": "string"}, "description": "Company domains e.g. ['triplewhale.com']"},
                "titles": {"type": "array", "items": {"type": "string"}, "description": "Job titles to filter by"},
                "seniorities": {"type": "array", "items": {"type": "string"}, "description": "['vp', 'director', 'c_suite', 'owner']"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["domains"],
        },
    },
    {
        "name": "apollo_enrich_contact",
        "description": "Get verified email and phone for a specific person at a company.",
        "input_schema": {
            "type": "object",
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "domain": {"type": "string", "description": "Company domain e.g. 'triplewhale.com'"},
                "linkedin_url": {"type": "string"},
            },
            "required": ["first_name", "domain"],
        },
    },
    {
        "name": "apollo_get_campaigns",
        "description": "List all active Apollo email sequences/campaigns.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "apollo_enroll_sequence",
        "description": "Enroll contact IDs into an Apollo email sequence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "contact_ids": {"type": "array", "items": {"type": "string"}},
                "campaign_id": {"type": "string"},
            },
            "required": ["contact_ids", "campaign_id"],
        },
    },
    {
        "name": "hubspot_create_deal",
        "description": "Create a new partnership deal in HubSpot CRM to track the opportunity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "deal_name": {"type": "string", "description": "e.g. 'Triple Whale — Rev Share Partnership'"},
                "stage": {"type": "string", "description": "'appointmentscheduled' (Prospected), 'qualifiedtobuy' (Contacted), 'presentationscheduled' (In Talks), 'closedwon' (Closed Won)"},
                "amount": {"type": "number", "description": "Estimated annual value in USD"},
                "deal_type": {"type": "string", "description": "e.g. 'Revenue Share', 'Flat Fee', 'Hybrid'"},
                "notes": {"type": "string"},
            },
            "required": ["company_name", "deal_name", "stage"],
        },
    },
    {
        "name": "hubspot_update_deal",
        "description": "Update an existing deal's stage, amount, or notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "deal_id": {"type": "string"},
                "stage": {"type": "string"},
                "amount": {"type": "number"},
                "notes": {"type": "string"},
            },
            "required": ["deal_id"],
        },
    },
    {
        "name": "hubspot_get_pipeline",
        "description": "Get all partnership deals from HubSpot, grouped by stage with total value.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stage_filter": {"type": "string", "description": "Optional: filter by pipeline stage"},
            },
        },
    },
    {
        "name": "hubspot_create_contact",
        "description": "Create a contact record in HubSpot for a partner prospect.",
        "input_schema": {
            "type": "object",
            "properties": {
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "email": {"type": "string"},
                "company": {"type": "string"},
                "job_title": {"type": "string"},
                "phone": {"type": "string"},
            },
            "required": ["first_name", "last_name", "email"],
        },
    },
]

# ════════════════════════════════════════════════════════════════════════════
# TOOL DISPATCHER
# ════════════════════════════════════════════════════════════════════════════

def dispatch_tool(name, inputs):
    try:
        if name == "apollo_search_companies":
            return apollo_search_companies(**inputs)
        elif name == "apollo_search_contacts":
            return apollo_search_contacts(**inputs)
        elif name == "apollo_enrich_contact":
            return apollo_enrich_contact(**inputs)
        elif name == "apollo_get_campaigns":
            return apollo_get_campaigns()
        elif name == "apollo_enroll_sequence":
            return apollo_enroll_sequence(**inputs)
        elif name == "hubspot_create_deal":
            return hubspot_create_deal(**inputs)
        elif name == "hubspot_update_deal":
            return hubspot_update_deal(**inputs)
        elif name == "hubspot_get_pipeline":
            return hubspot_get_pipeline(**inputs)
        elif name == "hubspot_create_contact":
            return hubspot_create_contact(**inputs)
        return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error ({name}): {str(e)}"

# ════════════════════════════════════════════════════════════════════════════
# AGENT SYSTEM PROMPT
# ════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an AI partnerships agent for AppLovin (NYSE: APP), a top-100 market cap company.
Your job: automate the full partnership lifecycle for the Growth Partnerships Manager.

Capabilities:
1. PROSPECT — Find B2B partners (Shopify apps, attribution SaaS, podcast networks, agencies) via Apollo
2. ENRICH — Find decision-makers and their verified contact info
3. OUTREACH — Draft personalized 3-touch email sequences
4. CRM — Create/update HubSpot deals for every prospect
5. REPORT — Summarize pipeline, flag stalled deals, calculate ROI vs. budget

AppLovin context:
- Mobile advertising platform, 1B+ user reach
- Target partners: companies whose customers are DTC/ecommerce advertisers
- 8-figure annual partnership budget, full P&L accountability
- Deal structures: flat fee, rev share, or hybrid

Work style:
- Be decisive and specific — always end with a clear next step
- Score every prospect 1-10 on partnership fit (how many of their customers could become AppLovin advertisers?)
- Create a HubSpot deal immediately when you identify a good prospect
- Keep outreach emails short, personalized, and value-forward
- When using tools, briefly say why before calling them"""

# ════════════════════════════════════════════════════════════════════════════
# AGENT LOOP
# ════════════════════════════════════════════════════════════════════════════

def run_agent(user_message, history):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    api_history = []
    for msg in history:
        if msg["role"] in ("user", "assistant"):
            api_history.append({"role": msg["role"], "content": msg["content"]})

    api_history.append({"role": "user", "content": user_message})

    with st.chat_message("assistant", avatar="🤖"):
        full_text = ""
        placeholder = st.empty()

        while True:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=ALL_TOOLS,
                messages=api_history,
            )

            text_parts = [b.text for b in response.content if b.type == "text"]
            tool_calls = [b for b in response.content if b.type == "tool_use"]

            if text_parts:
                chunk = "\n".join(text_parts)
                full_text += ("\n" if full_text else "") + chunk
                placeholder.markdown(full_text + ("▌" if tool_calls else ""))

            if response.stop_reason == "end_turn" or not tool_calls:
                placeholder.markdown(full_text)
                break

            for tc in tool_calls:
                st.markdown(
                    f'<div class="tool-call">⚙️ <b>{tc.name}</b><br>'
                    f'<code>{json.dumps(tc.input)[:300]}</code></div>',
                    unsafe_allow_html=True,
                )
                with st.spinner(f"Running {tc.name}..."):
                    result = dispatch_tool(tc.name, tc.input)
                st.markdown(
                    f'<div class="tool-result">✓ <pre style="margin:0;white-space:pre-wrap">'
                    f'{result[:800]}</pre></div>',
                    unsafe_allow_html=True,
                )
                st.session_state.messages.append({
                    "role": "tool", "tool": tc.name,
                    "input": tc.input, "result": result,
                })

            api_history.append({"role": "assistant", "content": response.content})
            api_history.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tc.id,
                 "content": dispatch_tool(tc.name, tc.input)}
                for tc in tool_calls
            ]})

    return full_text

# ════════════════════════════════════════════════════════════════════════════
# STREAMLIT UI
# ════════════════════════════════════════════════════════════════════════════

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.markdown("## 🤝 Partnerships Agent")
    st.caption("Claude + Apollo + HubSpot")
    st.divider()
    st.markdown("### ⚡ Quick Actions")
    quick_actions = {
        "🔍 Prospect Shopify Apps":       "Search Apollo for the top Shopify ecosystem apps to partner with — analytics, email, SMS, CX, loyalty. Score each 1-10 on fit and find the right decision-maker. Create HubSpot deals for the top 3.",
        "📊 View My Pipeline":             "Pull my full deal pipeline from HubSpot. Group by stage, show total value, flag stalled deals, give me my top 3 priority actions today.",
        "🎯 Prospect Podcast Networks":    "Find podcast networks with DTC/entrepreneur audiences for sponsorship deals. Target 500K+ monthly listeners. I want flat fee deals that drive AppLovin advertiser signups.",
        "🏢 Prospect Attribution SaaS":    "Find attribution and analytics SaaS tools used by DTC ecommerce brands — Triple Whale, Northbeam, Branch, Rockerbox. These are strategic integration + referral partnerships.",
        "📧 Draft Outreach — Triple Whale":"Find the right contact at triplewhale.com, enrich their email, draft a personalized Touch 1 outreach email, and create a HubSpot deal to track it.",
        "📅 Weekly Priorities":            "Based on the current pipeline, what are my top 5 most important actions this week to close the most valuable deals?",
    }
    for label, prompt in quick_actions.items():
        if st.button(label, key=label):
            st.session_state.pending_prompt = prompt

    st.divider()
    st.markdown("### 🔑 API Status")
    for name, key in [("Claude", "ANTHROPIC_API_KEY"), ("Apollo", "APOLLO_API_KEY"), ("HubSpot", "HUBSPOT_API_KEY")]:
        icon = "✅" if os.environ.get(key) else "❌"
        st.caption(f"{icon} {name}")

    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Header
st.markdown("""
<div class="main-header">
  <h1>🤖 AppLovin Growth Partnerships Agent</h1>
  <p>AI-powered deal sourcing · contact enrichment · CRM management · outreach sequencing</p>
</div>
""", unsafe_allow_html=True)

# Stats
c1, c2, c3, c4 = st.columns(4)
c1.metric("Tools Available", "9")
c2.metric("APIs Connected", "2 live")
c3.metric("Prospects Found", "15")
c4.metric("Pipeline Value", "$3.1M")

st.markdown("---")

# Chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(msg["content"])
    elif msg["role"] == "tool":
        with st.chat_message("assistant", avatar="⚙️"):
            st.markdown(
                f'<div class="tool-call">⚙️ <b>{msg["tool"]}</b> → '
                f'<code>{json.dumps(msg["input"])[:150]}</code></div>'
                f'<div class="tool-result">{msg["result"][:400]}</div>',
                unsafe_allow_html=True,
            )

# Handle quick action
if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("API keys not configured. Add them in Streamlit Cloud → App Settings → Secrets.")
    else:
        result = run_agent(prompt, st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": result})
    st.rerun()

# Chat input
if prompt := st.chat_input("Ask anything... e.g. 'Find Shopify apps to partner with'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("API keys not configured. Add them in Streamlit Cloud → App Settings → Secrets.")
    else:
        result = run_agent(prompt, st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": result})
    st.rerun()

# Empty state
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
