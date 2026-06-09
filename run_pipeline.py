import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Trust-Aware Memory Intelligence System (TAMIS)")
    parser.add_argument("--step", action="store_true", help="Run interactively step-by-step")
    parser.add_argument("--web", action="store_true", help="Launch web dashboard")
    parser.add_argument("--explain", nargs=2, metavar=("SUBJECT", "PREDICATE"), help="Explain a specific belief")
    
    args = parser.parse_args()
    
    # Ensure output dir exists
    os.makedirs("output", exist_ok=True)
    
    if args.web:
        print("Starting Streamlit Dashboard...")
        os.system("streamlit run streamlit_app.py")
        return

    from src.pipeline import Pipeline
    
    data_path = "data/claims.jsonl"
    mem_path = "output/memory_store.json"
    log_path = "output/change_log.json"
    
    pipeline = Pipeline(data_path, mem_path, log_path)
    pipeline.load_data()
    pipeline.load() # load existing memory if any
    
    if args.explain:
        subj, pred = args.explain
        res = pipeline.memory.explain(subj, pred)
        print(f"\n--- Explanation for {subj} {pred} ---")
        print(res)
        
        # Optionally ask LLM for natural language summary
        prov = []
        entry = pipeline.memory.query(subj, pred)
        if entry:
            prov = entry.provenance_history
            print("\nLLM Summary:")
            print(pipeline.llm.generate_explanation(subj, pred, entry.object, prov))
        return

    if args.step:
        print("Interactive Mode. Press Enter to process next claim, or type 'q' to quit.")
        while pipeline.current_idx < len(pipeline.claims):
            cmd = input(f"Process claim {pipeline.current_idx + 1}/{len(pipeline.claims)}? [Enter/q]: ")
            if cmd.lower() == 'q':
                break
            pipeline.step()
    else:
        print("Running full pipeline...")
        while pipeline.step():
            pass
        print("Done. Check output/ for memory_store.json and change_log.json")

if __name__ == "__main__":
    main()
