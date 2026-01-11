"""
BitNet XL API Server
OpenAI-compatible API for mlx-bitnet BitNet XL model

Provides chat completions endpoint compatible with Open Web UI
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncIterator
import json
import time
import sys
import os
import asyncio

# Add Python library path for Aragorn's local user installation
user_site_packages = os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages')
if os.path.exists(user_site_packages):
    sys.path.insert(0, user_site_packages)

# Add mlx-bitnet directory to path for custom modules
mlx_bitnet_dir = os.path.expanduser('~/mlx-bitnet')
sys.path.insert(0, mlx_bitnet_dir)

try:
    import mlx.core as mx
    from mlx.utils import tree_unflatten, tree_map
    from mlx_bitnet import BitnetForCausalLM, BitnetTokenizer, sanitize_config
    from configuration_bitnet import BitnetConfig
    MLX_AVAILABLE = True
except ImportError as e:
    MLX_AVAILABLE = False
    print(f"WARNING: mlx-bitnet not available: {e}. Server will run in mock mode.")

app = FastAPI(title="BitNet XL API", version="1.0.0")

# Global model storage
MODEL = None
TOKENIZER = None
MODEL_NAME = "mlx-bitnet-xl"


# Request/Response Models
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[dict]
    usage: dict


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "mlx-bitnet"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


def load_model():
    """Load the BitNet XL model on startup"""
    global MODEL, TOKENIZER
    
    if not MLX_AVAILABLE:
        print("MLX not available - running in mock mode")
        return
    
    try:
        # Change to mlx-bitnet directory
        model_dir = os.path.expanduser("~/mlx-bitnet")
        os.chdir(model_dir)
        
        print(f"Loading BitNet model from {model_dir}...")
        print("This may take 1-2 minutes...")
        
        # Load config
        config = BitnetConfig.from_pretrained("1bitLLM/bitnet_b1_58-xl")
        MODEL = BitnetForCausalLM(sanitize_config(config))
        
        # Load weights
        weights = mx.load("1bitLLM-bitnet_b1_58-xl.npz")
        
        # Fix the weight naming mismatch (lm_head.linear.weight -> lm_head.weight)
        weights_dict = dict(weights.items())
        if "lm_head.linear.weight" in weights_dict:
            weights_dict["lm_head.weight"] = weights_dict.pop("lm_head.linear.weight")
        
        # Unflatten and convert dtype
        weights = tree_unflatten(list(weights_dict.items()))
        weights = tree_map(lambda p: p.astype(mx.float16), weights)
        
        # Update model
        MODEL.update(weights)
        mx.eval(MODEL.parameters())
        
        # Load tokenizer
        TOKENIZER = BitnetTokenizer.from_pretrained("1bitLLM/bitnet_b1_58-xl")
        
        print("✅ Model loaded successfully!")
        
    except Exception as e:
        print(f"❌ ERROR loading model: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    load_model()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "model": MODEL_NAME,
        "mlx_available": MLX_AVAILABLE,
        "model_loaded": MODEL is not None
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy" if MODEL is not None else "degraded",
        "model": MODEL_NAME,
        "mlx_available": MLX_AVAILABLE,
        "model_loaded": MODEL is not None,
        "timestamp": int(time.time())
    }


@app.get("/v1/models")
async def list_models() -> ModelListResponse:
    """List available models (OpenAI-compatible)"""
    return ModelListResponse(
        data=[
            ModelInfo(
                id=MODEL_NAME,
                created=int(time.time()),
                owned_by="mlx-bitnet"
            )
        ]
    )


def format_messages_as_prompt(messages: List[Message]) -> str:
    """Convert chat messages to a single prompt"""
    # Simple format - can be enhanced with proper chat templates
    prompt_parts = []
    for msg in messages:
        role = msg.role.capitalize()
        content = msg.content
        prompt_parts.append(f"{role}: {content}")
    
    # Add Assistant prefix for response
    prompt_parts.append("Assistant:")
    return "\n".join(prompt_parts)


def generate_text(prompt: str, temperature: float, max_tokens: int) -> str:
    """Generate text using the BitNet model"""
    # Tokenize input
    inputs = TOKENIZER(prompt, return_tensors="np")
    input_ids = mx.array(inputs["input_ids"])
    
    # Create attention mask
    attention_mask = mx.ones_like(input_ids)
    
    # Generate - this returns a generator that yields tokens
    token_generator = MODEL.generate(input_ids, attention_mask, temp=temperature)
    
    # Collect all generated tokens
    generated_tokens = []
    for token in token_generator:
        # Expand dims to match input_ids shape (batch_size, seq_len)
        token = mx.expand_dims(token, axis=-1)
        generated_tokens.append(token)
        # Limit output length (generator produces ~50 tokens by default)
        if len(generated_tokens) >= min(max_tokens, 50):
            break
    
    # Concatenate input and generated tokens
    if generated_tokens:
        output_ids = mx.concatenate([input_ids] + generated_tokens, axis=-1)
    else:
        output_ids = input_ids
    
    # Decode output (convert MLX array to list for tokenizer)
    output_list = output_ids[0].tolist()
    response = TOKENIZER.decode(output_list, skip_special_tokens=True)
    
    # Remove the original prompt from response
    if response.startswith(prompt):
        response = response[len(prompt):].strip()
    
    return response


async def generate_stream(prompt: str, temperature: float, max_tokens: int) -> AsyncIterator[str]:
    """Generate streaming response"""
    
    if not MLX_AVAILABLE or MODEL is None:
        # Mock response for testing
        mock_text = "This is a mock response. The mlx-bitnet model is not loaded."
        for word in mock_text.split():
            chunk_id = f"chatcmpl-{int(time.time() * 1000)}"
            chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": MODEL_NAME,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": word + " "},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.1)
        
        # Send final chunk
        final_chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": MODEL_NAME,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        return
    
    # Real model inference with streaming
    try:
        chunk_id = f"chatcmpl-{int(time.time() * 1000)}"
        
        # Generate text
        response = generate_text(prompt, temperature, max_tokens)
        
        # Stream the response word by word
        words = response.split()
        for word in words:
            chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": MODEL_NAME,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": word + " "},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
        
        # Send final chunk
        final_chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": MODEL_NAME,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        error_chunk = {
            "error": {
                "message": f"Generation failed: {str(e)}",
                "type": "server_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    Generate chat completions (OpenAI-compatible)
    
    Supports both streaming and non-streaming modes
    """
    
    # Validate model name
    if request.model != MODEL_NAME:
        raise HTTPException(
            status_code=400,
            detail=f"Model {request.model} not found. Available: {MODEL_NAME}"
        )
    
    # Convert messages to prompt
    prompt = format_messages_as_prompt(request.messages)
    
    # Handle streaming
    if request.stream:
        return StreamingResponse(
            generate_stream(prompt, request.temperature, request.max_tokens),
            media_type="text/event-stream"
        )
    
    # Non-streaming response
    if not MLX_AVAILABLE or MODEL is None:
        # Mock response
        response_text = "This is a mock response. The mlx-bitnet model is not loaded."
    else:
        try:
            response_text = generate_text(prompt, request.temperature, request.max_tokens)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Generation failed: {str(e)}"
            )
    
    # Return OpenAI-compatible response
    response_id = f"chatcmpl-{int(time.time() * 1000)}"
    return ChatCompletionResponse(
        id=response_id,
        created=int(time.time()),
        model=MODEL_NAME,
        choices=[
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        usage={
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(prompt.split()) + len(response_text.split())
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8083,
        log_level="info"
    )
