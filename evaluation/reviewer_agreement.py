# Path: evaluation/reviewer_agreement.py
import numpy as np
import logging

logger = logging.getLogger(__name__)

def calculate_cohens_kappa(reviewer1_scores, reviewer2_scores):
    """
    Calculate Cohen's Kappa to measure the inter-rater agreement between two reviewers.
    Scores should be categorical (e.g., 1 for Reject, 2 for Revise, 3 for Accept).
    
    Returns:
        float: Cohen's Kappa score (between -1 and 1).
               <0: No agreement, 0-0.2: Slight, 0.2-0.4: Fair, 0.4-0.6: Moderate, 
               0.6-0.8: Substantial, 0.8-1.0: Almost perfect.
    """
    if len(reviewer1_scores) != len(reviewer2_scores):
        raise ValueError("Both reviewers must have evaluated the same number of proposals.")
        
    if len(reviewer1_scores) == 0:
        return 0.0

    r1 = np.array(reviewer1_scores)
    r2 = np.array(reviewer2_scores)
    
    # 1. Calculate Observed Agreement (Po)
    po = np.sum(r1 == r2) / len(r1)
    
    # 2. Calculate Expected Agreement by Chance (Pe)
    categories = np.unique(np.concatenate((r1, r2)))
    pe = 0.0
    for cat in categories:
        prob1 = np.sum(r1 == cat) / len(r1)
        prob2 = np.sum(r2 == cat) / len(r2)
        pe += prob1 * prob2
        
    # 3. Calculate Cohen's Kappa
    # Formula: k = (Po - Pe) / (1 - Pe)
    if pe == 1.0:
        return 1.0 # Perfect agreement where everyone always chooses the same category
        
    kappa = (po - pe) / (1 - pe)
    
    logger.info(f"Cohen's Kappa calculated: {kappa:.4f} (Observed: {po:.2f}, Expected: {pe:.2f})")
    return round(kappa, 4)

def identify_bias(reviewer1_scores, reviewer2_scores, kappa_threshold=0.4):
    """
    Analyzes the scores to flag potential biases if agreement is low.
    """
    kappa = calculate_cohens_kappa(reviewer1_scores, reviewer2_scores)
    
    result = {
        "kappa_score": kappa,
        "agreement_level": "Acceptable",
        "warning": None
    }
    
    if kappa < kappa_threshold:
        result["agreement_level"] = "Low"
        
        # Check who is stricter
        r1_mean = np.mean(reviewer1_scores)
        r2_mean = np.mean(reviewer2_scores)
        
        if r1_mean < r2_mean:
            result["warning"] = "Reviewer 1 is significantly stricter than Reviewer 2."
        elif r2_mean < r1_mean:
            result["warning"] = "Reviewer 2 is significantly stricter than Reviewer 1."
            
    return result

# --- Test the logic ---
if __name__ == "__main__":
    # Example: 1=Reject, 2=Revise, 3=Accept
    # Reviewer 1 is very strict (mostly 1s and 2s)
    rev1 = [1, 1, 2, 1, 3, 2, 1, 1, 2, 3]
    # Reviewer 2 is very lenient (mostly 2s and 3s)
    rev2 = [2, 2, 3, 1, 3, 3, 2, 1, 2, 3]
    
    analysis = identify_bias(rev1, rev2)
    print("Bias Analysis Results:")
    print(f"Kappa Score: {analysis['kappa_score']}")
    print(f"Agreement Level: {analysis['agreement_level']}")
    print(f"Warning: {analysis['warning']}")