import streamlit as st
import pandas as pd
from src.pipeline import Pipeline
import os

# Set page config
st.set_page_config(page_title="TAMIS Dashboard", layout="wide")

st.title("TAMIS - Trust-Aware Memory Intelligence System")

@st.cache_resource
def get_pipeline():
    data_path = "data/claims.jsonl"
    mem_path = "output/memory_store.json"
    log_path = "output/change_log.json"
    p = Pipeline(data_path, mem_path, log_path)
    p.load_data()
    p.load()
    return p

pipeline = get_pipeline()

# Sidebar Controls
st.sidebar.header("Controls")

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("Step Next Claim"):
        if pipeline.step():
            st.success("Processed 1 claim")
        else:
            st.warning("No more claims")
            
with col2:
    if st.button("Run All"):
        count = 0
        while pipeline.step():
            count += 1
        st.success(f"Processed {count} claims")

st.sidebar.markdown("---")
st.sidebar.metric("Processed Claims", f"{pipeline.current_idx} / {len(pipeline.claims)}")
active_memories = len([m for m in pipeline.memory.memories.values() if m.status == "active"])
st.sidebar.metric("Active Memories", active_memories)

# Main Content
tab1, tab2 = st.tabs(["Memory Store", "Change Log"])

with tab1:
    st.subheader("Memory Store")
    memories = list(pipeline.memory.memories.values())
    if memories:
        # Convert to dataframe for nice display
        df_data = []
        for m in memories:
            df_data.append({
                "Subject": m.subject,
                "Predicate": m.predicate,
                "Object": m.object,
                "Confidence": f"{m.confidence:.2f}",
                "Status": m.status,
                "Sources": ", ".join(m.sources)
            })
        df = pd.DataFrame(df_data)
        
        # Sort so active is at top
        df = df.sort_values(by=["Status", "Confidence"], ascending=[True, False])
        
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Explain a Belief")
        subjects = list(set([m.subject for m in memories]))
        if subjects:
            sel_subj = st.selectbox("Select Subject", subjects)
            preds = [m.predicate for m in memories if m.subject == sel_subj]
            sel_pred = st.selectbox("Select Predicate", preds)
            
            if st.button("Explain"):
                entry = pipeline.memory.query(sel_subj, sel_pred)
                if entry:
                    st.text(pipeline.memory.explain(sel_subj, sel_pred))
    else:
        st.info("No memories stored yet. Click 'Step Next Claim' to begin.")

with tab2:
    st.subheader("Change Log")
    logs = pipeline.memory.change_log
    if logs:
        # Reverse to show newest first
        for log in reversed(logs):
            with st.expander(f"[{log.action}] Claim {log.claim_id} - {log.timestamp[:19]}"):
                st.write(f"**Reason:** {log.reason}")
                if log.old_value or log.new_value:
                    st.write(f"**Value Change:** {log.old_value} -> {log.new_value}")
                st.write(f"**Confidence Delta:** {log.confidence_delta:+.2f}")
    else:
        st.info("No logs yet.")
