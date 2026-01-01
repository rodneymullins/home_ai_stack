"""Browser Use Web Interface with Gradio"""
import gradio as gr
import asyncio
from browser_agent import run_task
import config

# Available models from Ollama
AVAILABLE_MODELS = [
    "gpt-oss:20b",
    "llama3.1:8b",
    "gemma3:27b",
    "devstral-small-2:24b",
    "ministral-3:14b"
]

def execute_browser_task(task_description, model_name):
    """Execute browser task and return results"""
    if not task_description.strip():
        return "❌ Please enter a task description"
    
    try:
        result = asyncio.run(run_task(task_description, model_name))
        
        if result["success"]:
            return f"""✅ **Task Completed Successfully**

**Task:** {result['task']}
**Model:** {result['model']}

**Result:**
{result['result']}
"""
        else:
            return f"""❌ **Task Failed**

**Task:** {result['task']}
**Model:** {result['model']}

**Error:**
{result['error']}
"""
    except Exception as e:
        return f"❌ **Error:** {str(e)}"

# Example tasks
EXAMPLES = [
    ["Go to example.com and extract the main heading", "gpt-oss:20b"],
    ["Search Google for 'best practices for Docker security' and summarize the top 3 results", "gpt-oss:20b"],
    ["Go to news.ycombinator.com and extract the top 5 story titles", "llama3.1:8b"],
]

# Create Gradio interface
with gr.Blocks(title="Browser Use AI Agent", theme=gr.themes.Soft()) as interface:
    gr.Markdown("""
    # 🤖 Browser Use AI Agent
    
    AI-powered web browser automation using your local Ollama models.
    
    **What it can do:**
    - Navigate websites autonomously
    - Extract data from web pages  
    - Fill forms and interact with elements
    - Research and summarize information
    """)
    
    with gr.Row():
        with gr.Column(scale=2):
            task_input = gr.Textbox(
                label="Task Description",
                placeholder="e.g., Go to Wikipedia and search for 'Artificial Intelligence'",
                lines=3
            )
            model_dropdown = gr.Dropdown(
                choices=AVAILABLE_MODELS,
                value=config.DEFAULT_MODEL,
                label="Ollama Model"
            )
            submit_btn = gr.Button("🚀 Execute Task", variant="primary", size="lg")
        
        with gr.Column(scale=3):
            output = gr.Markdown(label="Result")
    
    gr.Examples(
        examples=EXAMPLES,
        inputs=[task_input, model_dropdown],
        label="Example Tasks"
    )
    
    submit_btn.click(
        fn=execute_browser_task,
        inputs=[task_input, model_dropdown],
        outputs=output
    )

if __name__ == "__main__":
    interface.launch(
        server_name="0.0.0.0",
        server_port=8001,
        share=False
    )
