"""
Domain Categorization System for Research Papers

Automatically categorizes papers into unified knowledge domains
regardless of source (ArXiv, PsyArXiv, SSRN, NBER, etc.)
"""

import re
from typing import Dict, List, Tuple

# Unified knowledge domain definitions
DOMAIN_KEYWORDS = {
    'economics': [
        'econom', 'macroeconom', 'microeconom', 'fiscal', 'monetary',
        'gdp', 'inflation', 'unemployment', 'labor market', 'growth',
        'trade', 'development', 'poverty', 'inequality'
    ],
    'finance': [
        'financ', 'portfolio', 'asset', 'investment', 'stock', 'bond',
        'derivatives', 'options', 'futures', 'risk management', 'hedge',
        'capital market', 'banking', 'credit', 'valuation', 'return'
    ],
    'psychology': [
        'psycholog', 'cognitive', 'behavioral', 'mental', 'brain',
        'neuroscience', 'development', 'child', 'psychiatry', 'therapy',
        'emotion', 'memory', 'learning', 'perception', 'personality'
    ],
    'quantitative_methods': [
        'econometric', 'statistic', 'regression', 'time series', 'panel data',
        'machine learning', 'neural network', 'forecast', 'prediction',
        'bayesian', 'maximum likelihood', 'causal', 'inference'
    ],
    'business': [
        'management', 'strategy', 'organization', 'marketing', 'accounting',
        'corporate', 'firm', 'entrepreneur', 'innovation', 'competition',
        'supply chain', 'operations', 'decision making'
    ],
    'social_sciences': [
        'sociology', 'political', 'policy', 'governance', 'institution',
        'education', 'demographic', 'social network', 'culture', 'public'
    ]
}

# Specific topic keywords (finer granularity)
TOPIC_KEYWORDS = {
    # Economics
    'behavioral_economics': ['behavioral', 'choice', 'decision', 'bias', 'heuristic'],
    'game_theory': ['game theory', 'nash equilibrium', 'strategic', 'cooperation'],
    'labor_economics': ['labor', 'employment', 'wage', 'unemployment', 'job'],
    'international_trade': ['trade', 'export', 'import', 'tariff', 'globalization'],
    
    # Finance  
    'behavioral_finance': ['behavioral finance', 'investor sentiment', 'market anomal'],
    'corporate_finance': ['corporate finance', 'capital structure', 'dividend', 'merger'],
    'asset_pricing': ['asset pricing', 'capm', 'factor model', 'risk premium'],
    'portfolio_theory': ['portfolio', 'diversification', 'allocation', 'optimization'],
    
    # Psychology
    'child_development': ['child development', 'infant', 'toddler', 'adolescent'],
    'clinical_psychology': ['clinical', 'therapy', 'treatment', 'disorder', 'intervention'],
    'cognitive_psychology': ['cognitive', 'memory', 'attention', 'perception', 'reasoning'],
    'developmental_psychology': ['developmental', 'lifespan', 'aging', 'maturation'],
    
    # Methods
    'machine_learning': ['machine learning', 'deep learning', 'neural network'],
    'causal_inference': ['causal', 'instrumental variable', 'diff-in-diff', 'rdd'],
    'time_series': ['time series', 'arima', 'var', 'cointegration', 'forecast']
}


def categorize_paper(title: str, abstract: str, source_categories: List[str] = None) -> Tuple[str, List[str], List[str]]:
    """
    Categorize a paper into unified knowledge domains
    
    Returns:
        (primary_domain, secondary_domains, specific_topics)
    """
    text = (title + " " + (abstract or "")).lower()
    
    # Score each domain
    domain_scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        domain_scores[domain] = score
    
    # Boost from source categories (ArXiv, etc.)
    if source_categories:
        for cat in source_categories:
            cat_lower = cat.lower()
            if 'econ' in cat_lower:
                domain_scores['economics'] = domain_scores.get('economics', 0) + 3
            if 'fin' in cat_lower or 'q-fin' in cat_lower:
                domain_scores['finance'] = domain_scores.get('finance', 0) + 3
            if 'psych' in cat_lower or 'cogn' in cat_lower:
                domain_scores['psychology'] = domain_scores.get('psychology', 0) + 3
            if 'stat' in cat_lower or 'math' in cat_lower:
                domain_scores['quantitative_methods'] = domain_scores.get('quantitative_methods', 0) + 2
    
    # Primary domain (highest score)
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    primary_domain = sorted_domains[0][0] if sorted_domains[0][1] > 0 else 'general'
    
    # Secondary domains (score >= 2 and not primary)
    secondary_domains = [d for d, s in sorted_domains[1:] if s >= 2][:2]
    
    # Specific topics
    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if sum(1 for kw in keywords if kw in text) >= 1:
            topics.append(topic)
    
    return primary_domain, secondary_domains, topics[:5]  # Max 5 topics


def get_source_categories(source: str, paper_data: dict) -> List[str]:
    """Extract categories from source-specific metadata"""
    if source == 'arxiv':
        return paper_data.get('categories', [])
    elif source == 'psyarxiv':
        return paper_data.get('subjects', [])
    elif source == 'ssrn':
        return paper_data.get('classifications', [])
    return []


# Example usage
if __name__ == "__main__":
    # Test categorization
    test_papers = [
        {
            'title': "Behavioral Economics and Child Development: Evidence from Field Experiments",
            'abstract': "We study how behavioral biases emerge in children using randomized controlled trials...",
            'source': 'psyarxiv'
        },
        {
            'title': "Portfolio Optimization Using Machine Learning",
            'abstract': "This paper applies deep neural networks to portfolio selection and risk management...",
            'source': 'arxiv',
            'categories': ['q-fin.PM']
        }
    ]
    
    for paper in test_papers:
        primary, secondary, topics = categorize_paper(
            paper['title'],
            paper.get('abstract', ''),
            paper.get('categories')
        )
        print(f"\nPaper: {paper['title'][:50]}...")
        print(f"Primary: {primary}")
        print(f"Secondary: {secondary}")
        print(f"Topics: {topics}")
