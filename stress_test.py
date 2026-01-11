import time
import os
import psycopg2
from ollama import Client
from neo4j import GraphDatabase
import concurrent.futures
import statistics
import random
from config import DB_CONFIG

# --- Config ---
WORKERS = 8 # Hammer with 8 threads
ITERATIONS = 50 # Per worker
THOR_IP = DB_CONFIG.get('host', 'localhost')  # From centralized config
OLLAMA_URL = f"http://{THOR_IP}:11434"
NEO4J_URI = f"bolt://{THOR_IP}:7687"
NEO4J_AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD", "homeai2025"))
PG_CONFIG = DB_CONFIG  # Use centralized config

def worker_task(worker_id):
    print(f"[{worker_id}] Starting...")
    client = Client(host=OLLAMA_URL)
    
    # DB Connections
    pg_conn = psycopg2.connect(**PG_CONFIG)
    pg_cur = pg_conn.cursor()
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, encrypted=False)
    
    times = []
    
    try:
        for i in range(ITERATIONS):
            start = time.time()
            try:
                # 1. Generate Embedding (CPU Heavy)
                text = f"Stress test data worker {worker_id} iteration {i} " + "content " * 20
                emb = client.embeddings(model="nomic-embed-text:latest", prompt=text)
                
                # 2. Postgres Write (I/O)
                pg_cur.execute("INSERT INTO stress_test (worker, iter, data) VALUES (%s, %s, %s)", 
                               (worker_id, i, str(emb['embedding'][:10])))
                pg_conn.commit()
                
                # 3. Neo4j Write (Graph)
                with neo4j_driver.session() as session:
                    session.run("CREATE (n:StressNode {worker: $w, iter: $i})", w=worker_id, i=i)
                
                duration = time.time() - start
                times.append(duration)
                if i % 10 == 0:
                    print(f"[{worker_id}] Iter {i}: {duration:.4f}s")
                    
            except Exception as e:
                print(f"[{worker_id}] Error: {e}")
                
    finally:
        pg_cur.close()
        pg_conn.close()
        neo4j_driver.close()
        
    avg = statistics.mean(times) if times else 0
    print(f"[{worker_id}] Finished. Avg Latency: {avg:.4f}s")
    return times

def setup_db():
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS stress_test (id SERIAL PRIMARY KEY, worker INT, iter INT, data TEXT);")
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    print(f"🔥 Starting THOR STRESS TEST ({WORKERS} Workers, {ITERATIONS} Iters) 🔥")
    setup_db()
    
    start_total = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(worker_task, i) for i in range(WORKERS)]
        concurrent.futures.wait(futures)
        
    total_time = time.time() - start_total
    total_ops = WORKERS * ITERATIONS
    print(f"\n✅ Stress Test Complete.")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Throughput: {total_ops/total_time:.2f} transactions/sec (Embedding+PG+Neo4j)")
