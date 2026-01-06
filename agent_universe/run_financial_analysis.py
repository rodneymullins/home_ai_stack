# run_financial_analysis.py
import os
import sys

sys.path.append(os.getcwd())

try:
    from agentuniverse.base.config.application_configer.app_configer import AppConfiger
    from agentuniverse.base.config.application_configer.application_config_manager import ApplicationConfigManager
    from agentuniverse.base.config.configer import Configer
    from agentuniverse.agent.agent_manager import AgentManager
    from agentuniverse.base.config.component_configer.configers.agent_configer import AgentConfiger
    from agentuniverse.base.config.component_configer.configers.llm_configer import LLMConfiger
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def run_doe_workflow(topic: str):
    print(f"🚀 Starting DOE Workflow for: {topic}")
    
    # 1. Load Config
    config_path = os.path.join(os.getcwd(), 'config/config.toml')
    print(f"Loading config from: {config_path}")
    
    # Standard Framework Initialization
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.base.util.logging.logging_config import LoggingConfig
    
    # Pre-configure logging to avoid default path permission issues if config load fails
    LoggingConfig.log_path = '/Users/rod/agent_universe_doe/logs'
    LoggingConfig.log_level = 'INFO'
    
    AgentUniverse().start(config_path=config_path)
    
    from agentuniverse.agent.action.tool.tool_manager import ToolManager
    from agentuniverse.llm.llm_manager import LLMManager
    print("\n[DEBUG] Registered Tools:", ToolManager().get_instance_obj_list())
    print("[DEBUG] Registered LLMs:", LLMManager().get_instance_obj_list())
    
    # 3. Data Agent
    print("\n[DEBUG] Registered Agents:", AgentManager().get_instance_obj_list())
    print("\n[DATA AGENT] Fetching info...")
    try:
        data_agent = AgentManager().get_instance_obj('data_agent')
        if not data_agent:
             print("Error: 'data_agent' not found in registry.")
        else:
            data_result = data_agent.run(input=f"Get financial data for {topic}.")
            print(f"Data Result: {data_result}")
    except Exception as e:
        print(f"Data Agent Failed: {e}")
        data_result = {"price": 250.00, "trend": "volatile"}

    # 4. Opinion Agent
    print("\n[OPINION AGENT] Analyzing...")
    try:
        opinion_agent = AgentManager().get_instance_obj('opinion_agent')
        if opinion_agent:
            opinion_result = opinion_agent.run(input=f"Analyze: {data_result}")
            print(f"Opinion Result: {opinion_result}")
    except Exception as e:
        print(f"Opinion Agent Failed: {e}")

if __name__ == "__main__":
    run_doe_workflow("Tesla (TSLA)")
