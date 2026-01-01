from neo4j import GraphDatabase
import os

uri = "bolt://192.168.1.211:7687"
user = "neo4j"
password = os.getenv("NEO4J_PASSWORD", "homeai2025")

try:
    print(f"Connecting to Neo4j at {uri}...")
    driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
    
    print("Verifying connectivity...")
    driver.verify_connectivity()
    print("✅ Connected!")
    
    with driver.session() as session:
        result = session.run("RETURN 'Neo4j is working' AS message")
        msg = result.single()["message"]
        print(f"Server says: {msg}")
        
    driver.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
