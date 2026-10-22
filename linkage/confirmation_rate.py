import logging
from ingestion.openalex_connector import search_published_papers

logger = logging.getLogger(__name__)

def calculate_confirmation_rate(self_reported_papers: list) -> float:
    """
    Calculates the Confirmation Rate of self-reported papers by verifying them via OpenAlex.
    """
    logger.info(f"Starting verification for {len(self_reported_papers)} self-reported papers...")
    
    confirmed_count = 0
    verification_results = []
    
    for paper in self_reported_papers:
        title = paper.get("title")
        logger.info(f"Verifying: '{title}'")
        
        # Fetch the first 3 results from OpenAlex for matching
        search_results = search_published_papers(title, max_results=3)
        
        # validate if any of the search results match the self-reported title (case-insensitive)
        is_confirmed = any(
            title.lower() in res['title'].lower() or res['title'].lower() in title.lower() 
            for res in search_results if res['title']
        )
        
        if is_confirmed:
            confirmed_count += 1
            verification_results.append((title, "✅ Confirmed"))
        else:
            verification_results.append((title, "❌ Not Found"))
            
    confirmation_rate = (confirmed_count / len(self_reported_papers)) * 100
    
    print("\n" + "="*50)
    print("📊 Confirmation Rate Report")
    print("="*50)
    for res in verification_results:
        print(f"{res[1]} - {res[0][:60]}...")
    print("-" * 50)
    print(f"Total Claimed: {len(self_reported_papers)}")
    print(f"Total Verified: {confirmed_count}")
    print(f"Confirmation Rate: {confirmation_rate:.1f}%")
    print("="*50)
    
    return confirmation_rate

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Data for testing the confirmation rate calculation
    sample_self_reported = [
        {"title": "SoK: On the Semantic AI Security in Autonomous Driving", "author": "Smith"}, # بحث حقيقي
        {"title": "An Ontology-Driven AI Framework for Context-Aware Threat Detection in Mobile Health Applications", "author": "Ali"}, # بحث حقيقي
        {"title": "Fake Paper on 6G Networks that was never published", "author": "John Doe"} # بحث غير حقيقي
    ]
    
    calculate_confirmation_rate(sample_self_reported)