import requests
import json
import os
from typing import List, Dict, Any, Optional


class LLMService:
    def __init__(self):
        self.inference_url = "https://openrouter.ai/api/v1/chat/completions"
        self.default_timeout = 30
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = "anthropic/claude-sonnet-4"
        self.default_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "MCP Backend"
        }

    def chat_with_assistant(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a chat request to the OpenRouter API
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            system_prompt: Optional system prompt to guide the assistant
        
        Returns:
            Dict containing the API response
        """
        
        # Default system prompt for MCP server generation
        default_system = """You are an expert MCP server developer. Your task is to create a complete, working MCP server based on the user's requirements.

# MCP Server Creation Guide

MCP (Model Context Protocol) servers are Python applications that provide tools and resources to AI assistants.

## Basic Structure

```python
import asyncio
from mcp import Tool
from mcp.server import Server
from mcp.tools import Tool
from typing import Any

app = Server("your-server-name")

@app.tool()
async def your_tool_name(arg1: str, arg2: int = 10) -> str:
    \"\"\"
    Description of what your tool does.
    
    Args:
        arg1: Description of first argument
        arg2: Description of second argument (optional, defaults to 10)
    
    Returns:
        Description of return value
    \"\"\"
    # Your tool implementation here
    return f"Result: {arg1} with {arg2}"

if __name__ == "__main__":
    asyncio.run(app.run())
```

## Key Components

1. **Server**: The main MCP server instance
2. **Tools**: Functions decorated with @app.tool() that the AI can call
3. **Resources**: Data or files the AI can access (use @app.resource())
4. **Prompts**: Pre-defined prompts the AI can use (use @app.prompt())

## Tool Guidelines

- Use clear, descriptive function names
- Include comprehensive docstrings
- Add type hints for all parameters
- Handle errors gracefully
- Return meaningful results

## Example Tools

```python
@app.tool()
async def get_weather(city: str) -> str:
    \"\"\"Get current weather for a city\"\"\"
    # Weather API call implementation
    return f"Weather in {city}: Sunny, 75°F"

@app.tool() 
async def calculate_tip(bill_amount: float, tip_percentage: float = 0.18) -> dict:
    \"\"\"Calculate tip and total for a bill\"\"\"
    tip = bill_amount * tip_percentage
    total = bill_amount + tip
    return {"tip": tip, "total": total, "bill": bill_amount}
```

Always ensure your MCP server follows these patterns for proper integration.

## Response Format

You MUST respond with a JSON object containing exactly these three fields:

{
  "code": "// Complete Python MCP server code here",
  "next_steps": "Clear instructions for what the user needs to do next to deploy this MCP server, or congratulations message if objective is fully achieved",
  "is_deployable": true/false
}

Guidelines:
- code: Generate complete, functional Python code with all necessary imports, error handling, descriptive names, comprehensive docstrings, and production-ready implementation
- next_steps: If code needs external dependencies, API keys, or deployment steps, explain what's needed. If fully complete and deployable, congratulate the user
- is_deployable: Set to true only if the MCP server is complete and can be deployed without additional requirements

Always return valid JSON in this exact format."""

        # Prepare messages with system prompt
        api_messages = []
        if system_prompt or default_system:
            api_messages.append({
                "role": "system",
                "content": system_prompt or default_system
            })
        
        api_messages.extend(messages)
        
        # Prepare the OpenRouter payload
        payload = {
            "model": self.model,
            "messages": api_messages
        }
        
        try:
            response = requests.post(
                self.inference_url,
                headers=self.default_headers,
                json=payload,
                timeout=self.default_timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}: {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {str(e)}")

    def extract_content(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and parse structured content from the OpenRouter API response
        
        Args:
            api_response: The response from the OpenRouter API
            
        Returns:
            Parsed content with code, next_steps, and is_deployable fields
        """
        try:
            # OpenRouter returns response in choices[0].message.content format
            if "choices" in api_response and len(api_response["choices"]) > 0:
                choice = api_response["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
                    
                    # Try to parse as JSON
                    try:
                        parsed_content = json.loads(content)
                        
                        # Validate required fields
                        if all(key in parsed_content for key in ["code", "next_steps", "is_deployable"]):
                            return parsed_content
                        else:
                            # Fallback: return raw content with default structure
                            return {
                                "code": content,
                                "next_steps": "Please review the generated code and make any necessary adjustments.",
                                "is_deployable": False
                            }
                    except json.JSONDecodeError:
                        # Fallback: return raw content with default structure
                        return {
                            "code": content,
                            "next_steps": "Please review the generated code and make any necessary adjustments.",
                            "is_deployable": False
                        }
            
            return {
                "code": "",
                "next_steps": "No response generated. Please try again.",
                "is_deployable": False
            }
        except (KeyError, IndexError, TypeError):
            return {
                "code": "",
                "next_steps": "Error parsing response. Please try again.",
                "is_deployable": False
            }

    def format_messages_for_api(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Format messages for the API request
        
        Args:
            messages: List of ChatMessage objects or dicts
            
        Returns:
            Formatted messages for API
        """
        formatted_messages = []
        
        for message in messages:
            # Handle both ChatMessage objects and dicts
            if hasattr(message, 'role') and hasattr(message, 'content'):
                formatted_messages.append({
                    "role": message.role,
                    "content": message.content
                })
            elif isinstance(message, dict) and 'role' in message and 'content' in message:
                formatted_messages.append({
                    "role": message['role'],
                    "content": message['content']
                })
        
        return formatted_messages


llm_service = LLMService()