-- Research Papers Database Schema
-- Database: research_papers

CREATE TABLE IF NOT EXISTS papers (
    id SERIAL PRIMARY KEY,
    
    -- Source identifiers (one per source)
    arxiv_id VARCHAR(50),
    psyarxiv_id VARCHAR(50),
    ssrn_id VARCHAR(50),
    nber_id VARCHAR(50),
    pubmed_id VARCHAR(50),
    semantic_scholar_id VARCHAR(50),
    doi VARCHAR(100),
    
    -- Basic metadata
    title TEXT NOT NULL,
    authors TEXT[],
    abstract TEXT,
    published_date DATE,
    updated_date DATE,
    
    -- Source tracking
    source VARCHAR(20) CHECK (source IN ('arxiv', 'psyarxiv', 'ssrn', 'nber', 'pubmed', 'semantic', 'biorxiv')),
    source_url TEXT,
    pdf_url TEXT,
    pdf_path TEXT,
    
    -- Unified knowledge domain categorization
    primary_domain VARCHAR(50), -- 'economics', 'psychology', 'finance', 'quantitative_methods', 'business', 'social_sciences'
    secondary_domains VARCHAR(50)[],
    specific_topics TEXT[], -- 'child_development', 'behavioral_finance', 'econometrics', etc.
    
    -- Publication details
    journal VARCHAR(255),
    journal_impact_factor DECIMAL(5,2),
    publication_status VARCHAR(50), -- 'preprint', 'published', 'accepted'
    peer_reviewed BOOLEAN DEFAULT FALSE,
    
    -- Quality metrics
    quality_score DECIMAL(3,2), -- 0-10 weighted quality score
    citation_count INTEGER DEFAULT 0,
    influence_score DECIMAL(5,2), -- From Semantic Scholar
    
    -- Author quality indicators
    author_affiliations TEXT[],
    author_h_index_avg DECIMAL(5,2),
    top_institution BOOLEAN DEFAULT FALSE, -- MIT, Stanford, Harvard, etc.
    
    -- Processing metadata
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    mem0_stored BOOLEAN DEFAULT FALSE,
    embedding_generated BOOLEAN DEFAULT FALSE,
    last_quality_check TIMESTAMP,
    
    -- Unique constraint to prevent duplicates across sources
    UNIQUE NULLS NOT DISTINCT (arxiv_id, psyarxiv_id, ssrn_id, nber_id, pubmed_id, doi)
);

CREATE TABLE IF NOT EXISTS paper_summaries (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER REFERENCES papers(id) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    summary_type VARCHAR(50) DEFAULT 'llm_generated',
    generated_at TIMESTAMP DEFAULT NOW(),
    model_used VARCHAR(100)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
CREATE INDEX IF NOT EXISTS idx_papers_primary_domain ON papers(primary_domain);
CREATE INDEX IF NOT EXISTS idx_papers_secondary_domains ON papers USING GIN(secondary_domains);
CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_papers_quality ON papers(quality_score DESC) WHERE quality_score >= 3.0;
CREATE INDEX IF NOT EXISTS idx_papers_mem0 ON papers(mem0_stored);
CREATE INDEX IF NOT EXISTS idx_papers_title ON papers USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_papers_abstract ON papers USING GIN(to_tsvector('english', abstract));
CREATE INDEX IF NOT EXISTS idx_papers_topics ON papers USING GIN(specific_topics);

-- Source-specific ID indexes
CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id) WHERE arxiv_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_papers_ssrn ON papers(ssrn_id) WHERE ssrn_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_papers_nber ON papers(nber_id) WHERE nber_id IS NOT NULL;

-- Full-text search function
CREATE OR REPLACE FUNCTION search_papers(search_query TEXT)
RETURNS TABLE (
    paper_id INTEGER,
    title TEXT,
    authors TEXT[],
    published_date DATE,
    source VARCHAR(20),
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.title,
        p.authors,
        p.published_date,
        p.source,
        ts_rank(
            to_tsvector('english', p.title || ' ' || COALESCE(p.abstract, '')),
            plainto_tsquery('english', search_query)
        ) AS rank
    FROM papers p
    WHERE to_tsvector('english', p.title || ' ' || COALESCE(p.abstract, ''))
        @@ plainto_tsquery('english', search_query)
    ORDER BY rank DESC;
END;
$$ LANGUAGE plpgsql;
