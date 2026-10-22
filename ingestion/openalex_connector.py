import requests
import logging

logger = logging.getLogger(__name__)

def reconstruct_abstract(inverted_index: dict) -> str:
    """
    OpenAlex returns abstracts as an inverted index to save space.
    This function rebuilds the original abstract string.
    """
    if not inverted_index:
        return ""
    
    try:
        # Find the length of the abstract
        max_idx = max([max(positions) for positions in inverted_index.values()])
        words = [""] * (max_idx + 1)
        
        # Place each word in its correct position
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
                
        return " ".join(words).strip()
    except Exception as e:
        logger.warning(f"Failed to reconstruct abstract: {e}")
        return ""

def search_published_papers(query: str, max_results: int = 5, mailto: str = "fahad.alfaifi@example.com") -> list:
    """
    Search OpenAlex for published papers matching the proposal title or keywords.
    Adding 'mailto' puts us in the 'Polite Pool' for faster API responses.
    """
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per_page": max_results,
        "mailto": mailto  # Replace with your actual academic/project email
    }
    
    logger.info(f"Querying OpenAlex for: '{query}'")
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    data = response.json()
    results = []
    
    for work in data.get("results", []):
        abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
        
        paper_data = {
            "openalex_id": work.get("id"),
            "doi": work.get("doi"),
            "title": work.get("title", ""),
            "publication_year": work.get("publication_year"),
            "authors": [a["author"]["display_name"] for a in work.get("authorships", [])],
            "abstract": abstract
        }
        results.append(paper_data)
        
    return results

# Test the function with a sample query
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_query = "AI driven semantic drift detection in academic proposals"
    papers = search_published_papers(sample_query, max_results=2)
    
    for idx, paper in enumerate(papers, 1):
        print(f"\n--- Result {idx} ---")
        print(f"Title: {paper['title']}")
        print(f"Year: {paper['publication_year']}")
        print(f"Abstract Preview: {paper['abstract'][:150]}...")