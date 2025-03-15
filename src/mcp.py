from typing import Dict, Any, Optional
import logging
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from .config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = None
try:
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
    else:
        logger.debug(f"Found OPENAI_API_KEY: {api_key[:8]}...")
        openai_client = AsyncOpenAI(api_key=api_key)
        logger.info("Successfully initialized OpenAI client in MCP")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client in MCP: {str(e)}")
    logger.exception("Detailed error:")

async def mcp_request(
    request_type: str,
    params: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Handle various types of AI model requests through a unified interface
    
    Args:
        request_type (str): Type of request (e.g., "generate_response", "embed_text")
        params (Dict[str, Any]): Parameters for the request
        
    Returns:
        Optional[Dict[str, Any]]: Response from the model or None if error
    """
    try:
        if request_type == "generate_response":
            if not openai_client:
                logger.error("OpenAI client not initialized")
                return None
                
            # Extract parameters
            prompt = params.get("prompt", "")
            max_tokens = params.get("max_tokens", 1000)
            temperature = params.get("temperature", settings.TEMPERATURE)
            model = params.get("model", settings.OPENAI_MODEL)
            
            # Generate response using GPT-4
            response = await openai_client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract and return the response content
            if response and response.choices:
                return {
                    "content": response.choices[0].message.content,
                    "model": model,
                    "finish_reason": response.choices[0].finish_reason
                }
            else:
                logger.error("No content in OpenAI response")
                return None
                
        else:
            logger.error(f"Unknown request type: {request_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error in MCP request: {str(e)}")
        return None 