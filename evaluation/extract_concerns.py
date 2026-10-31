# Path: evaluation/extract_concerns.py
import re
import logging
from collections import Counter
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

logger = logging.getLogger(__name__)

def clean_text(text):
    """
    Clean the text by removing special characters, numbers, and converting to lowercase.
    """
    if not isinstance(text, str):
        return ""
    # Remove punctuation and numbers
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    return text.lower().strip()

def extract_recurring_concerns(reviews_list, top_n=5):
    """
    Extract the most frequent meaningful keywords (concerns) from reviewer comments using NLP.
    
    Args:
        reviews_list (list of str): List of free-text comments from reviewers.
        top_n (int): Number of top concerns to return.
        
    Returns:
        list of tuples: A list containing the top concerns and their frequencies.
    """
    # 1. Combine and clean all reviews
    all_text = " ".join([clean_text(review) for review in reviews_list])
    
    # 2. Tokenize (split into words)
    words = all_text.split()
    
    # 3. Custom list of academic/project specific stop words to ignore
    custom_stop_words = {'proposal', 'research', 'project', 'study', 'paper', 'reviewer'}
    all_stop_words = set(ENGLISH_STOP_WORDS).union(custom_stop_words)
    
    # 4. Filter out stop words and short words (length < 3)
    meaningful_words = [word for word in words if word not in all_stop_words and len(word) > 2]
    
    # 5. Count frequencies
    word_counts = Counter(meaningful_words)
    
    # 6. Extract the top N concerns
    top_concerns = word_counts.most_common(top_n)
    
    logger.info(f"Extracted Top {top_n} recurring concerns: {top_concerns}")
    return top_concerns

# --- Test the Logic ---
if __name__ == "__main__":
    # Sample Mock Data for testing
    sample_reviews = [
        "The proposal lacks a clear methodology and the budget is unclear.",
        "Methodology is very weak. The budget seems inflated.",
        "Good research, but the dataset size is too small.",
        "Unclear dataset acquisition plan. Methodology needs revision.",
        "The project is ambitious, but budget constraints might be an issue."
    ]
    
    print("Analyzing Reviewer Comments for Concerns...\n")
    concerns = extract_recurring_concerns(sample_reviews, top_n=4)
    
    print("Top Recurring Concerns:")
    for concern, count in concerns:
        print(f"- '{concern.capitalize()}': mentioned {count} times")