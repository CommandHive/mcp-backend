import requests
import json
import os
import re
from typing import List, Dict, Any, Optional
from prompts.constants import (
    CHAT_SESSION_SYSTEM_PROMPT,
    MCP_SERVER_GENERATION_SYSTEM_PROMPT,
    FALLBACK_NEXT_STEPS_REVIEW,
    FALLBACK_NEXT_STEPS_NO_RESPONSE,
    FALLBACK_NEXT_STEPS_ERROR
)


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

    def chat_with_assistant(self, messages: List[Dict[str, str]], chat_session_id: Optional[str], is_new_session: bool = False) -> Dict[str, Any]:
        """
        Send a chat request to the OpenRouter API
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            chat_session_id: The chat session ID (if any)
            is_new_session: True if this is a new session, False if continuing existing
        
        Returns:
            Dict containing the API response
        """
        
        # Use appropriate system prompt based on whether this is a new session
        if is_new_session:
            default_system = MCP_SERVER_GENERATION_SYSTEM_PROMPT
        else:
            default_system = CHAT_SESSION_SYSTEM_PROMPT

        print(f"[chat_with_assistant] Using system prompt: {default_system}")
        # Prepare messages with system prompt
        api_messages = []
        if default_system:
            api_messages.append({
                "role": "system",
                "content": default_system
            })
        
        api_messages.extend(messages)
        
        # Prepare the OpenRouter payload
        payload = {
            "model": self.model,
            "messages": api_messages
        }
        
        try:
            print(f"present payload: {payload}")
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
                    print(f"[extract_content] Raw content received from API: {len(content)} characters")
                    
                    # Try to parse XML tags
                    try:
                        # Extract code block
                        code_match = re.search(r'<code>(.*?)</code>', content, re.DOTALL)
                        code = code_match.group(1).strip() if code_match else ""
                        
                        # Extract next_steps
                        next_steps_match = re.search(r'<next_steps>(.*?)</next_steps>', content, re.DOTALL)
                        next_steps = next_steps_match.group(1).strip() if next_steps_match else ""
                        
                        # Extract is_deployable
                        deployable_match = re.search(r'<is_deployable>(.*?)</is_deployable>', content, re.DOTALL)
                        is_deployable_str = deployable_match.group(1).strip().lower() if deployable_match else "false"
                        is_deployable = is_deployable_str == "true"
                        
                        if code_match and next_steps_match and deployable_match:
                            print("[extract_content] Successfully parsed XML from API response")
                            
                            # Create dict for validation
                            parsed_data = {
                                "code": code,
                                "next_steps": next_steps,
                                "is_deployable": is_deployable
                            }
                            
                            # Validate using Pydantic
                            return parsed_data
                        else:
                            print("[extract_content] XML parsing failed - missing required tags")
                            print(f"[extract_content] Found tags: code={bool(code_match)}, next_steps={bool(next_steps_match)}, is_deployable={bool(deployable_match)}")
                            print("[extract_content] Using fallback structure with raw content")
                            # Fallback: return raw content with default structure
                            return {
                                "code": content,
                                "next_steps": FALLBACK_NEXT_STEPS_REVIEW,
                                "is_deployable": False
                            }
                    except Exception as e:
                        print(f"[extract_content] XML parsing failed with error: {e}")
                        print("[extract_content] Using fallback structure with raw content")
                        # Fallback: return raw content with default structure
                        return {
                            "code": content,
                            "next_steps": FALLBACK_NEXT_STEPS_REVIEW,
                            "is_deployable": False
                        }
            
            print("[extract_content] No valid content found in API response")
            return {
                "code": "",
                "next_steps": FALLBACK_NEXT_STEPS_NO_RESPONSE,
                "is_deployable": False
            }
        except (KeyError, IndexError, TypeError) as e:
            print(f"[extract_content] Error parsing API response structure: {e}")
            return {
                "code": "",
                "next_steps": FALLBACK_NEXT_STEPS_ERROR,
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