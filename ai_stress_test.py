#!/usr/bin/env python3
"""
AI Services Stress Test - Exo and Ollama
"""

import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_result(name, value, unit=""):
    print(f"{Colors.GREEN}  ✓ {name}: {Colors.BLUE}{value} {unit}{Colors.END}")

# Test Exo API
def test_exo():
    print_header("Exo Inference Engine Test")
    
    try:
        # Check if API is responsive
        start = time.time()
        response = requests.get("http://localhost:8000/v1/models", timeout=10)
        api_time = time.time() - start
        
        if response.status_code == 200:
            print_result("API Response Time", f"{api_time*1000:.2f}", "ms")
            models = response.json().get('data', [])
            print_result("Available Models", len(models), "")
            
            if models:
                for model in models:
                    print_result("Model", model.get('id', 'Unknown'), "")
            
            # Simple inference test
            prompt = "Hello, how are you?"
            payload = {
                "model": "llama-3.2-1b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            start = time.time()
            response = requests.post(
                "http://localhost:8000/v1/chat/completions",
                json=payload,
                timeout=30
            )
            inference_time = time.time() - start
            
            if response.status_code == 200:
                print_result("Single Inference Time", f"{inference_time:.2f}", "s")
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    response_text = result['choices'][0]['message']['content']
                    print_result("Response Length", len(response_text), "chars")
                    print(f"{Colors.YELLOW}  Response: {response_text[:100]}...{Colors.END}")
                
                return {"api_time_ms": api_time*1000, "inference_time_s": inference_time}
            else:
                print(f"{Colors.RED}  ✗ Inference failed: {response.status_code}{Colors.END}")
                return None
        else:
            print(f"{Colors.RED}  ✗ API not ready: {response.status_code}{Colors.END}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"{Colors.RED}  ✗ Exo API timeout - service may still be loading model{Colors.END}")
        return None
    except Exception as e:
        print(f"{Colors.RED}  ✗ Exo test failed: {e}{Colors.END}")
        return None

# Test Ollama API
def test_ollama():
    print_header("Ollama Inference Engine Test")
    
    try:
        # Check if API is responsive
        start = time.time()
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        api_time = time.time() - start
        
        if response.status_code == 200:
            print_result("API Response Time", f"{api_time*1000:.2f}", "ms")
            models = response.json().get('models', [])
            print_result("Available Models", len(models), "")
            
            if models:
                for model in models[:5]:  # Show first 5
                    print_result("Model", model.get('name', 'Unknown'), "")
                
                # Use first available model for testing
                test_model = models[0]['name']
                
                # Simple inference test
                payload = {
                    "model": test_model,
                    "prompt": "Hello, how are you?",
                    "stream": False
                }
                
                start = time.time()
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json=payload,
                    timeout=30
                )
                inference_time = time.time() - start
                
                if response.status_code == 200:
                    print_result("Single Inference Time", f"{inference_time:.2f}", "s")
                    result = response.json()
                    response_text = result.get('response', '')
                    print_result("Response Length", len(response_text), "chars")
                    print(f"{Colors.YELLOW}  Response: {response_text[:100]}...{Colors.END}")
                    
                    return {"api_time_ms": api_time*1000, "inference_time_s": inference_time, "model": test_model}
                else:
                    print(f"{Colors.RED}  ✗ Inference failed: {response.status_code}{Colors.END}")
                    return None
            else:
                print(f"{Colors.YELLOW}  ! No models available{Colors.END}")
                return {"status": "no_models"}
        else:
            print(f"{Colors.RED}  ✗ API not ready: {response.status_code}{Colors.END}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"{Colors.RED}  ✗ Ollama API timeout{Colors.END}")
        return None
    except Exception as e:
        print(f"{Colors.RED}  ✗ Ollama test failed: {e}{Colors.END}")
        return None

# Network throughput test
def test_network():
    print_header("Network Performance Test")
    
    try:
        # Test localhost throughput
        start = time.time()
        response = requests.get("http://localhost:3000", timeout=5)
        web_time = time.time() - start
        
        if response.status_code == 200:
            print_result("Open WebUI Response", f"{web_time*1000:.2f}", "ms")
            print_result("Response Size", f"{len(response.content) / 1024:.2f}", "KB")
            return {"webui_time_ms": web_time*1000}
        else:
            print(f"{Colors.YELLOW}  ! Web UI returned {response.status_code}{Colors.END}")
            return None
            
    except Exception as e:
        print(f"{Colors.RED}  ✗ Network test failed: {e}{Colors.END}")
        return None

def main():
    print(f"\n{Colors.BOLD}╔════════════════════════════════════════════════════════════╗")
    print(f"║          AI SERVICES STRESS TEST SUITE                     ║")
    print(f"║              {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                        ║")
    print(f"╚════════════════════════════════════════════════════════════╝{Colors.END}\n")
    
    results = {}
    
    results['network'] = test_network()
    results['ollama'] = test_ollama()
    results['exo'] = test_exo()
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v is not None)
    total = len(results)
    print_result("Tests Passed", f"{passed}/{total}", "")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/tmp/ai_stress_test_{timestamp}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print_result("Results saved to", results_file, "")
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}✓ AI stress test completed!{Colors.END}\n")

if __name__ == "__main__":
    main()
