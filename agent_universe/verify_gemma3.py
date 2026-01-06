#!/usr/bin/env python3
"""Quick verification that Gemma 3 270M is registered"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.llm.llm_manager import LLMManager
from agentuniverse.base.util.logging.logging_config import LoggingConfig

def verify_gemma3():
    print("🔍 Verifying Gemma 3 270M Registration\n")
    
    config_path = os.path.join(os.getcwd(), 'config/config.toml')
    LoggingConfig.log_path = '/Users/rod/agent_universe_doe/logs'
    LoggingConfig.log_level = 'INFO'
    
    AgentUniverse().start(config_path=config_path)
    
    # Check LLMs
    print("[LLM Check]")
    llms = LLMManager().get_instance_obj_list()
    gemma3_found = False
    for llm in llms:
        if 'gemma3' in llm.name.lower():
            print(f"  ✅ {llm.name}: {llm.model_name} ({llm.api_base})")
            gemma3_found = True
    
    if not gemma3_found:
        print("  ❌ Gemma 3 270M not found!")
        return False
    
    # Check Data Agent
    print("\n[Agent Check]")
    try:
        data_agent = AgentManager().get_instance_obj('data_agent')
        llm_name = data_agent.agent_model.profile.get('llm_model', {}).get('name')
        print(f"  ✅ Data Agent LLM: {llm_name}")
        
        if llm_name != 'gemma3_270m_llm':
            print(f"  ⚠️  Expected 'gemma3_270m_llm', got '{llm_name}'")
        
    except Exception as e:
        print(f"  ❌ Data Agent check failed: {e}")
        return False
    
    print("\n✅ All checks passed!")
    return True

if __name__ == "__main__":
    verify_gemma3()
