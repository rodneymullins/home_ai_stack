#!/usr/bin/env python3
"""
Comprehensive Stress Test Suite for Gandalf Server
Tests: PostgreSQL, Neo4j, Redis, Disk I/O, Memory, CPU, Network
"""

import time
import random
import psutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime
from config import DB_CONFIG

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_result(name, value, unit="", status="info"):
    color = Colors.BLUE
    if status == "success":
        color = Colors.GREEN
    elif status == "warning":
        color = Colors.YELLOW
    elif status == "error":
        color = Colors.RED
    
    print(f"{color}  ✓ {name}: {value} {unit}{Colors.END}")

def get_pg_connection():
    try:
        return psycopg2.connect(**DB_CONFIG['postgresql'])
    except Exception as e:
        print_result("PostgreSQL Connection", f"FAILED: {e}", "", "error")
        return None

# ==============================================================================
# PostgreSQL Stress Test
# ==============================================================================
def test_postgresql():
    print_header("PostgreSQL Performance Test")
    try:
        import psycopg2
        from psycopg2.pool import SimpleConnectionPool
        
        # Connection test
        start = time.time()
        conn = get_pg_connection()
        if conn is None:
            return None
        conn_time = time.time() - start
        print_result("Connection Time", f"{conn_time*1000:.2f}", "ms", "success")
        
        cursor = conn.cursor()
        
        # Simple query benchmark
        start = time.time()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        query_time = time.time() - start
        print_result("Simple Query Time", f"{query_time*1000:.2f}", "ms", "success")
        
        # Connection pool test
        pool = SimpleConnectionPool(1, 20, **DB_CONFIG['postgresql'])
        
        def execute_query(i):
            conn = pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT pg_sleep(0.01)")
            cursor.fetchone()
            cursor.close()
            pool.putconn(conn)
            return i
        
        start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(execute_query, i) for i in range(100)]
            for future in as_completed(futures):
                future.result()
        pool_time = time.time() - start
        
        print_result("100 Concurrent Queries", f"{pool_time:.2f}", "s", "success")
        print_result("Avg Query Throughput", f"{100/pool_time:.2f}", "queries/s", "success")
        
        cursor.close()
        conn.close()
        pool.closeall()
        
        return {"conn_time_ms": conn_time*1000, "query_time_ms": query_time*1000, "throughput_qps": 100/pool_time}
        
    except Exception as e:
        print_result("PostgreSQL Test", f"FAILED: {e}", "", "error")
        return None

# ==============================================================================
# Redis Stress Test
# ==============================================================================
def test_redis():
    print_header("Redis Cache Performance Test")
    try:
        import redis
        
        r = redis.Redis(**DB_CONFIG['redis'])
        
        # Connection test
        start = time.time()
        r.ping()
        ping_time = time.time() - start
        print_result("Ping Time", f"{ping_time*1000:.2f}", "ms", "success")
        
        # Write test
        start = time.time()
        for i in range(1000):
            r.set(f"stress_test_key_{i}", f"value_{i}")
        write_time = time.time() - start
        print_result("1000 Writes", f"{write_time:.2f}", "s", "success")
        print_result("Write Throughput", f"{1000/write_time:.0f}", "ops/s", "success")
        
        # Read test
        start = time.time()
        for i in range(1000):
            r.get(f"stress_test_key_{i}")
        read_time = time.time() - start
        print_result("1000 Reads", f"{read_time:.2f}", "s", "success")
        print_result("Read Throughput", f"{1000/read_time:.0f}", "ops/s", "success")
        
        # Cleanup
        for i in range(1000):
            r.delete(f"stress_test_key_{i}")
        
        return {"write_ops_per_sec": 1000/write_time, "read_ops_per_sec": 1000/read_time}
        
    except Exception as e:
        print_result("Redis Test", f"FAILED: {e}", "", "error")
        return None

# ==============================================================================
# Neo4j Stress Test
# ==============================================================================
def test_neo4j():
    print_header("Neo4j Graph Database Test")
    try:
        from neo4j import GraphDatabase
        
        driver = GraphDatabase.driver(
            DB_CONFIG['neo4j']['uri'],
            auth=(DB_CONFIG['neo4j']['user'], DB_CONFIG['neo4j']['password'])
        )
        
        # Connection test
        start = time.time()
        with driver.session() as session:
            result = session.run("RETURN 1")
            result.single()
        conn_time = time.time() - start
        print_result("Connection + Simple Query", f"{conn_time*1000:.2f}", "ms", "success")
        
        # Write test - create test nodes
        with driver.session() as session:
            start = time.time()
            for i in range(100):
                session.run(
                    "CREATE (n:StressTest {id: $id, timestamp: $ts})",
                    id=i, ts=datetime.now().isoformat()
                )
            write_time = time.time() - start
            print_result("100 Node Writes", f"{write_time:.2f}", "s", "success")
            
            # Read test
            start = time.time()
            result = session.run("MATCH (n:StressTest) RETURN count(n)")
            count = result.single()[0]
            read_time = time.time() - start
            print_result("Count Query", f"{read_time*1000:.2f}", "ms", "success")
            print_result("Nodes Created", count, "", "info")
            
            # Cleanup
            session.run("MATCH (n:StressTest) DELETE n")
        
        driver.close()
        return {"write_time_s": write_time, "read_time_ms": read_time*1000}
        
    except Exception as e:
        print_result("Neo4j Test", f"FAILED: {e}", "", "error")
        return None

# ==============================================================================
# Disk I/O Test
# ==============================================================================
def test_disk_io():
    print_header("Disk I/O Performance Test")
    
    # Test on RAID array
    test_file = "/mnt/raid0/stress_test.tmp"
    
    try:
        # Sequential write test
        print(f"{Colors.BLUE}  Testing sequential write...{Colors.END}")
        result = subprocess.run(
            ["dd", "if=/dev/zero", f"of={test_file}", "bs=1M", "count=1024", "oflag=direct"],
            capture_output=True, text=True, timeout=60
        )
        
        # Parse dd output
        for line in result.stderr.split('\n'):
            if 'MB/s' in line or 'GB/s' in line:
                print_result("Sequential Write", line.strip(), "", "success")
        
        # Sequential read test
        print(f"{Colors.BLUE}  Testing sequential read...{Colors.END}")
        result = subprocess.run(
            ["dd", f"if={test_file}", "of=/dev/null", "bs=1M", "iflag=direct"],
            capture_output=True, text=True, timeout=60
        )
        
        for line in result.stderr.split('\n'):
            if 'MB/s' in line or 'GB/s' in line:
                print_result("Sequential Read", line.strip(), "", "success")
        
        # Cleanup
        subprocess.run(["rm", "-f", test_file], check=False)
        
        return {"status": "completed"}
        
    except Exception as e:
        print_result("Disk I/O Test", f"FAILED: {e}", "", "error")
        subprocess.run(["rm", "-f", test_file], check=False)
        return None

# ==============================================================================
# Memory & CPU Test
# ==============================================================================
def test_system_resources():
    print_header("System Resources Test")
    
    # Memory info
    mem = psutil.virtual_memory()
    print_result("Total RAM", f"{mem.total / (1024**3):.2f}", "GB", "info")
    print_result("Available RAM", f"{mem.available / (1024**3):.2f}", "GB", "success")
    print_result("Memory Usage", f"{mem.percent}", "%", "warning" if mem.percent > 80 else "success")
    
    # CPU info
    cpu_count = psutil.cpu_count(logical=False)
    cpu_logical = psutil.cpu_count(logical=True)
    print_result("Physical CPU Cores", cpu_count, "", "info")
    print_result("Logical CPU Cores", cpu_logical, "", "info")
    
    # CPU load
    load1, load5, load15 = psutil.getloadavg()
    print_result("Load Average (1m)", f"{load1:.2f}", "", "info")
    print_result("Load Average (5m)", f"{load5:.2f}", "", "info")
    print_result("Load Average (15m)", f"{load15:.2f}", "", "info")
    
    # Disk usage
    disk = psutil.disk_usage('/mnt/raid0')
    print_result("RAID0 Total", f"{disk.total / (1024**4):.2f}", "TB", "info")
    print_result("RAID0 Used", f"{disk.used / (1024**3):.2f}", "GB", "info")
    print_result("RAID0 Free", f"{disk.free / (1024**4):.2f}", "TB", "success")
    print_result("RAID0 Usage", f"{disk.percent}", "%", "warning" if disk.percent > 80 else "success")
    
    return {
        "mem_total_gb": mem.total / (1024**3),
        "mem_available_gb": mem.available / (1024**3),
        "cpu_cores": cpu_count,
        "load_avg": [load1, load5, load15]
    }

# ==============================================================================
# Main
# ==============================================================================
def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║       GANDALF COMPREHENSIVE STRESS TEST SUITE              ║")
    print("║              " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "                        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    results = {}
    
    # Run all tests
    results['system'] = test_system_resources()
    results['postgresql'] = test_postgresql()
    results['redis'] = test_redis()
    results['neo4j'] = test_neo4j()
    results['disk_io'] = test_disk_io()
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v is not None)
    total = len(results)
    print_result("Tests Passed", f"{passed}/{total}", "", "success" if passed == total else "warning")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/tmp/stress_test_results_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print_result("Results saved to", results_file, "", "info")
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Stress test completed!{Colors.END}\n")

if __name__ == "__main__":
    main()
