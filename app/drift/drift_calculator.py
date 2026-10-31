import os
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import json

def calculate_drift():
    print("Starting Semantic Drift Calculation...")
    
    # 1. Define Paths
    input_file = "data/synthetic_drift_calibration_50.csv"
    output_dir = "results/drift"
    output_file = f"{output_dir}/drift_scores.csv"
    status_file = f"{output_dir}/execution_status.json"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Load the Data
    try:
        df = pd.read_csv(input_file, encoding='utf-8-sig')
        print(f"Loaded {len(df)} records from {input_file}")
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}. Please ensure Member C's data is present.")
        return

    # 3. Load the Model (Qwen/Qwen3-Embedding-0.6B)
    print("Loading Qwen embedding model. This might take a moment...")
    try:
        # trust_remote_code=True is often needed for Qwen models in huggingface
        model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Please ensure sentence-transformers is installed: pip install sentence-transformers einops")
        return

    # 4. Calculate Embeddings and Similarity
    print("Calculating embeddings and similarity scores...")
    similarities = []
    
    # We assume the CSV has columns like 'proposal_abstract' (or 'proposal_text') and 'publication_abstract' (or 'publication_text')
    # Let's check columns to be safe, defaulting to expected names if we don't know the exact ones.
    col_proposal = 'proposal_abstract' if 'proposal_abstract' in df.columns else df.columns[1] # fallback
    col_publication = 'publication_abstract' if 'publication_abstract' in df.columns else df.columns[2] # fallback
    
    for index, row in df.iterrows():
        prop_text = str(row[col_proposal])
        pub_text = str(row[col_publication])
        
        # Get embeddings
        emb_prop = model.encode([prop_text])
        emb_pub = model.encode([pub_text])
        
        # Calculate Cosine Similarity
        sim = cosine_similarity(emb_prop, emb_pub)[0][0]
        similarities.append(sim)
        
    df['similarity'] = similarities
    
    # 5. Define Threshold and Drift Flag
    # A standard threshold might be 0.7. Below this means it drifted.
    threshold = 0.70 
    df['threshold'] = threshold
    
    # If similarity is less than threshold, it's flagged as drift (True)
    df['drift_flag'] = df['similarity'] < df['threshold']
    
    # Mocking n_papers since this is a 1-to-1 synthetic pair calibration
    # If there is a real column, use it, otherwise set to 1.
    df['n_papers'] = 1 
    
    # Ensure grant_id exists
    col_id = 'grant_id' if 'grant_id' in df.columns else df.columns[0]
    
    # 6. Format the Final Output DataFrame
    final_df = pd.DataFrame({
        'grant_id': df[col_id],
        'similarity': df['similarity'],
        'threshold': df['threshold'],
        'drift_flag': df['drift_flag'],
        'n_papers': df['n_papers']
    })
    
    # Save the CSV
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Success! Drift scores saved to: {output_file}")
    
    # 7. Update the Status JSON
    try:
        with open(status_file, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
            
        status_data['model_scoring_status'] = 'completed'
        status_data['reason_model_scoring_not_run'] = None
        status_data['limitations'] = [lim for lim in status_data.get('limitations', []) if "pending actual Qwen embeddings" not in lim]
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=4)
        print(f"Updated status file: {status_file}")
    except FileNotFoundError:
         print("Note: execution_status.json not found to update, skipping.")

if __name__ == "__main__":
    calculate_drift()
