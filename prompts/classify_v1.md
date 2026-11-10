---
version: v1.0
purpose: Zero-shot bilingual research priority classification and semantic drift scoring
target_model: Qwen/Qwen3-Embedding-0.6B
commit_hash: 97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3
fields: title, keywords, abstract, background
drift_columns: proposal_abstract, publication_title
default_drift_threshold: 0.55
---
# Version: v1.0

Encode bilingual research texts into unit-normalized 1024-d vectors and compute cosine similarity.
