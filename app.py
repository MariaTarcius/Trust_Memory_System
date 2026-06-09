import streamlit as st
import pandas as pd
import json
import os

from database.init_db import init_db, DB_PATH
from graph.workflow import TAMISWorkflow
from agents.explainability_agent import ExplainabilityAgent

# Initialize DB if it doesn't exist
if not os.path.exists(DB_PATH):
    init_db()

st.set_page_config(page_title="TAMIS LangGraph Dashboard", layout="wide")
st.title("TAMIS - LangGraph & LangChain Architecture")

@st.cache_resource
def get_workflow():
    return TAMISWorkflow()

workflow = get_workflow()

# State management for data
if 'claims' not in st.session_state:
    claims = []
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'claims.json')
    if os.path.exists(data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    claims.append(json.loads(line))
        # Sort by timestamp
        claims.sort(key=lambda c: c.get('timestamp') or "9999-12-31T23:59:59Z")
    st.session_state.claims = claims
    st.session_state.current_idx = 0

# Sidebar
st.sidebar.header("Controls")
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("Step Next Claim"):
        idx = st.session_state.current_idx
        if idx < len(st.session_state.claims):
            claim = st.session_state.claims[idx]
            with st.spinner(f"Processing Claim {claim.get('id')}..."):
                res = workflow.process_claim(claim)
                st.success(f"Claim {claim.get('id')} processed! Decision: {res.get('final_decision')}")
            st.session_state.current_idx += 1
        else:
            st.warning("No more claims")

with col2:
    if st.button("Run All"):
        count = 0
        with st.spinner("Processing all remaining claims..."):
            while st.session_state.current_idx < len(st.session_state.claims):
                claim = st.session_state.claims[st.session_state.current_idx]
                workflow.process_claim(claim)
                st.session_state.current_idx += 1
                count += 1
        st.success(f"Processed {count} claims!")

st.sidebar.markdown("---")
st.sidebar.metric("Processed Claims", f"{st.session_state.current_idx} / {len(st.session_state.claims)}")

# Main Content
tab1, tab2, tab3 = st.tabs(["Memory Store", "Explainability", "Change Log"])

with tab1:
    st.subheader("Active Memories")
    active_mems = workflow.memory.get_all_active()
    if active_mems:
        df_data = []
        for m in active_mems:
            df_data.append({
                "Subject": m['subject'],
                "Predicate": m['predicate'],
                "Object": m['object'],
                "Confidence": f"{m['confidence']:.2f}",
                "Sources": ", ".join(m['sources'])
            })
        df = pd.DataFrame(df_data)
        df = df.sort_values(by="Confidence", ascending=False)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No active memories yet.")

with tab2:
    st.subheader("Explain a Belief")
    if active_mems:
        subjects = list(set([m['subject'] for m in active_mems]))
        sel_subj = st.selectbox("Select Subject", subjects)
        preds = [m['predicate'] for m in active_mems if m['subject'] == sel_subj]
        sel_pred = st.selectbox("Select Predicate", preds)
        
        if st.button("Generate Explanation"):
            exp_agent = ExplainabilityAgent(workflow.llm, workflow.memory)
            with st.spinner("Generating LLM explanation..."):
                res = exp_agent.explain(sel_subj, sel_pred)
                
            if "error" in res:
                st.error(res["error"])
            else:
                st.markdown(f"**LLM Summary**: {res['llm_explanation']}")
                st.markdown("### Provenance Timeline")
                for p in reversed(res['provenance_timeline']):
                    st.write(f"- **{p['timestamp'][:19]}**: [{p['action']}] {p['explanation']} (Conf: {p['confidence_before']:.2f} -> {p['confidence_after']:.2f})")
    else:
        st.info("Process claims first.")

with tab3:
    st.subheader("Change Log")
    logs = workflow.change_log.get_all()
    if logs:
        for log in reversed(logs):
            with st.expander(f"[{log['action']}] Claim {log['claim_id']} - {log['timestamp'][:19]}"):
                st.write(f"**Reason:** {log['reason']}")
                if log['old_value'] or log['new_value']:
                    st.write(f"**Value Change:** {log['old_value']} -> {log['new_value']}")
                st.write(f"**Confidence Delta:** {log['confidence_delta']:+.2f}")
    else:
        st.info("No logs yet.")
