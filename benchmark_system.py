import time
import os
import psycopg2
from ollama import Client
from neo4j import GraphDatabase
import statistics
from config import DB_CONFIG, GANDALF_IP, OLLAMA_HOST

# --- Config (from centralized config) ---
THOR_IP = GANDALF_IP
OLLAMA_URL = OLLAMA_HOST
NEO4J_URI = f"bolt://{THOR_IP}:7687"
NEO4J_AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD", "homeai2025"))
PG_CONFIG = DB_CONFIG

def benchmark_ollama():
    print(f"\n--- 🤖 Benchmarking Ollama ({OLLAMA_URL}) ---")
    client = Client(host=OLLAMA_URL)
    text = "The quick brown fox jumps over the lazy dog." * 10
    
    start = time.time()
    try:
        client.embeddings(model="nomic-embed-text:latest", prompt=text)
        duration = time.time() - start
        print(f"✅ Embedding (Standard): {duration:.4f}s")
        return duration
    except Exception as e:
        print(f"❌ Ollama Failed: {e}")
        return None

def benchmark_postgres():
    print(f"\n--- 🐘 Benchmarking Postgres ({THOR_IP}) ---")
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cur = conn.cursor()
        
        # Setup table
        cur.execute("CREATE TABLE IF NOT EXISTS bench_test (id SERIAL PRIMARY KEY, data TEXT);")
        conn.commit()
        
        # Write Test
        start = time.time()
        for i in range(100):
            cur.execute("INSERT INTO bench_test (data) VALUES (%s)", (f"test_data_{i}",))
        conn.commit()
        write_duration = time.time() - start
        print(f"✅ Write (100 inserts): {write_duration:.4f}s ({(100/write_duration):.2f} ops/s)")
        
        # Read Test
        start = time.time()
        cur.execute("SELECT * FROM bench_test LIMIT 100")
        cur.fetchall()
        read_duration = time.time() - start
        print(f"✅ Read (100 rows): {read_duration:.4f}s")
        
        # Cleanup
        cur.execute("DROP TABLE bench_test;")
        conn.commit()
        cur.close()
        conn.close()
        return write_duration
    except Exception as e:
        print(f"❌ Postgres Failed: {e}")
        return None

def benchmark_neo4j():
    print(f"\n--- 🕸️ Benchmarking Neo4j ({NEO4J_URI}) ---")
    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, encrypted=False)
        
        def create_nodes(tx):
            for i in range(100):
                tx.run("CREATE (n:BenchNode {id: $id})", id=i)
                
        # Write Test
        start = time.time()
        with driver.session() as session:
            session.execute_write(create_nodes)
        write_duration = time.time() - start
        print(f"✅ Write (100 nodes): {write_duration:.4f}s ({(100/write_duration):.2f} nodes/s)")
        
        # Cleanup
        with driver.session() as session:
            session.run("MATCH (n:BenchNode) DELETE n")
            
        driver.close()
        return write_duration
    except Exception as e:
        print(f"❌ Neo4j Failed: {e}")
        if driver: driver.close()
        return None

if __name__ == "__main__":
    print(f"🚀 Starting System Benchmark for Gandalf ({THOR_IP})...")
    
    # Run tests
    ollama_time = benchmark_ollama()
    pg_time = benchmark_postgres()
    neo4j_time = benchmark_neo4j()
    
    print("\nBenchmark Complete.")
