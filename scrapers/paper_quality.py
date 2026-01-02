"""
Research Paper Quality Scoring System

Weights and filters high-quality papers based on multiple criteria:
- Citation count
- Author reputation (h-index, affiliations)
- Peer review status
- Journal impact factor
- Recency
"""

def calculate_quality_score(paper_data):
    """
    Calculate quality score (0-10) for a research paper
    
    Criteria:
    - Citations: 0-3 points (log scale)
    - Author reputation: 0-2 points (h-index average)
    - Peer review status: 0-2 points
    - Journal impact: 0-2 points
    - Recency bonus: 0-1 points (papers < 1 year old)
    """
    score = 0.0
    
    # Citation score (0-3 points, logarithmic)
    citations = paper_data.get('citation_count') or 0
    if citations > 0:
        import math
        score += min(3.0, math.log10(citations + 1) * 1.5)
    
    # Author reputation (0-2 points)
    avg_h_index = paper_data.get('author_h_index_avg') or 0
    if avg_h_index > 0:
        score += min(2.0, avg_h_index / 25)  # h-index of 50+ = full points
    
    # Peer review status (0-2 points)
    status = paper_data.get('publication_status', 'preprint')
    if status == 'published':
        score += 2.0
    elif status == 'accepted':
        score += 1.5
    elif paper_data.get('peer_reviewed'):
        score += 1.0
    
    # Journal impact factor (0-2 points)
    impact_factor = paper_data.get('journal_impact_factor') or 0
    if impact_factor > 0:
        score += min(2.0, impact_factor / 5)  # IF of 10+ = full points
    
    # Recency bonus (0-1 point for papers < 1 year old)
    from datetime import datetime, timedelta, date
    pub_date = paper_data.get('published_date')
    if pub_date:
        # Convert date to datetime if needed
        if isinstance(pub_date, date) and not isinstance(pub_date, datetime):
            pub_date = datetime.combine(pub_date, datetime.min.time())
        if isinstance(pub_date, datetime):
            # Make timezone-naive for comparison
            if pub_date.tzinfo is not None:
                pub_date = pub_date.replace(tzinfo=None)
            age_days = (datetime.now() - pub_date).days
            if age_days < 365:
                score += (365 - age_days) / 365
    
    return round(min(10.0, score), 2)


# Quality thresholds for filtering
QUALITY_THRESHOLDS = {
    'minimum_score': 0.0,  # Temporarily disabled for testing - will be 3.0
    'high_quality': 6.0,   # Flag papers >= 6 as high quality
    'premium': 8.0         # Premium papers >= 8
}


def should_store_paper(paper_data):
    """Determine if paper meets minimum quality threshold"""
    score = calculate_quality_score(paper_data)
    return score >= QUALITY_THRESHOLDS['minimum_score']


def get_author_affiliations(authors):
    """
    Extract top-tier university affiliations
    Returns list of prestigious institutions
    """
    TOP_INSTITUTIONS = {
        'MIT', 'Stanford', 'Harvard', 'Cambridge', 'Oxford',
        'ETH', 'Berkeley', 'Princeton', 'Yale', 'Caltech',
        'Chicago', 'Columbia', 'Cornell', 'NYU', 'UPenn',
        'Carnegie Mellon', 'Northwestern', 'Duke', 'Michigan',
        'LSE', 'Imperial', 'UCL', 'National Bureau of Economic Research',
        'NBER', 'Federal Reserve', 'World Bank', 'IMF'
    }
    
    affiliations = []
    for author in authors:
        affiliation = getattr(author, 'affiliation', '')
        if affiliation:
            # Check for top institutions
            for inst in TOP_INSTITUTIONS:
                if inst.lower() in affiliation.lower():
                    if inst not in affiliations:
                        affiliations.append(inst)
                    break
    
    return affiliations


def estimate_author_h_index(author_name):
    """
    Estimate author h-index (placeholder for actual API integration)
    
    In production, integrate with:
    - Google Scholar API
    - Semantic Scholar API
    - ORCID API
    """
    # TODO: Implement actual h-index lookup
    # For now, return None to indicate unknown
    return None
