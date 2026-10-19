# Experiment 3: Cross-Lingual Validity Report (Arabic <-> English)

## 1. Model Configuration
- **Model ID:** `Qwen/Qwen3-Embedding-0.6B`
- **Commit Hash (Locked):** `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`
- **Sample Size:** `50` manual bilingual pairs (Arabic & English)

## 2. Quantitative Results
| Metric | Value |
| :--- | :--- |
| **Mean Cosine Similarity (Matching Pairs)** | `0.7381 ± 0.0255` |
| **Mean Cosine Similarity (Non-Matching Pairs)** | `0.5444` |
| **Discrimination Margin (Positive - Negative)** | `+0.1937` |
| **Top-1 Cross-Lingual Retrieval Accuracy** | `98.0% (49/50)` |
| **Top-3 Cross-Lingual Retrieval Accuracy** | `100.0% (50/50)` |

## 3. Conclusion
The model demonstrates strong cross-lingual alignment between Arabic and English research texts, achieving a clear separation margin of `0.1937` between matching and non-matching pairs.
