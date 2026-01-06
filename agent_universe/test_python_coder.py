#!/usr/bin/env python3
"""Test script for Python Coder Agent"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.input_object import InputObject
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.base.config.configer import Configer
from agentuniverse.llm.llm_manager import LLMManager

def test_python_coder():
    print("🧪 Testing Python Coder Agent\n")
    
    # 1. Initialize Framework
    config_path = os.path.join(os.getcwd(), 'config/config.toml')
    print(f"Loading config from: {config_path}")
    
    from agentuniverse.base.util.logging.logging_config import LoggingConfig
    LoggingConfig.log_path = '/Users/rod/agent_universe_doe/logs'
    LoggingConfig.log_level = 'INFO'
    
    AgentUniverse().start(config_path=config_path)
    
    # 2. Verify Registration
    print("\n[DEBUG] Registered LLMs:")
    llms = LLMManager().get_instance_obj_list()
    for llm in llms:
        if 'qwen' in llm.name.lower():
            print(f"  ✓ {llm.name}: {llm.model_name}")
    
    print("\n[DEBUG] Registered Agents:")
    agents = AgentManager().get_instance_obj_list()
    for agent in agents:
        if 'python' in agent.agent_model.info.get('name', '').lower():
            print(f"  ✓ {agent.agent_model.info.get('name')}")
    
    # 3. Test Python Code Generation
    print("\n[TEST] Generating Python code...")
    try:
        python_agent = AgentManager().get_instance_obj('python_coder_agent')
        
        input_obj = InputObject(params={
            'input': "Write a Python function that calculates the Fibonacci sequence up to n terms using dynamic programming."
        })
        
        result = python_agent.run(input=input_obj)
        
        print("\n✅ Generated Code:")
        print("=" * 60)
        print(result.get_data('output'))
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_python_coder()
