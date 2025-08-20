import requests
import json
import os
import re
import boto3
from botocore.exceptions import ClientError
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
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.default_timeout = 30
        print(os.getenv("OPENROUTER_API_KEY"))
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = "anthropic/claude-3.5-haiku"
        self.bedrock_model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"
        self.bedrock_region = os.getenv("AWS_REGION", "us-east-1")
        
        self.openrouter_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "MCP Backend"
        }
        
        # Initialize Bedrock client
        try:
            self.bedrock_client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self.bedrock_region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
        except Exception as e:
            print(f"Warning: Failed to initialize Bedrock client: {e}")
            self.bedrock_client = None

    def chat_with_assistant(self, messages: List[Dict[str, str]], chat_session_id: Optional[str], is_new_session: bool = False, provider: str = "bedrock") -> Dict[str, Any]:
        """
        Send a chat request to the specified LLM provider
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            chat_session_id: The chat session ID (if any)
            is_new_session: True if this is a new session, False if continuing existing
            provider: The LLM provider to use ("openrouter" or "bedrock")
        
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
        
        if provider == "bedrock":
            return self._chat_with_bedrock(api_messages)
        else:
            return self._chat_with_openrouter(api_messages)

    def _chat_with_openrouter(self, api_messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Send request to OpenRouter API"""
        payload = {
            "model": self.model,
            "messages": api_messages
        }
        
        try:
            print(f"[OpenRouter] Sending payload: {payload}")
            response = requests.post(
                self.openrouter_url,
                headers=self.openrouter_headers,
                json=payload,
                timeout=self.default_timeout
            )
            print(f"[OpenRouter] API response status code: {response.status_code}")
            
            if response.status_code != 200:
                raise Exception(f"OpenRouter API request failed with status {response.status_code}: {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenRouter request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from OpenRouter: {str(e)}")

    def _chat_with_bedrock(self, api_messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Send request to AWS Bedrock API using boto3"""
        if not self.bedrock_client:
            raise Exception("Bedrock client not initialized. Check AWS credentials and region.")
        
        # Convert messages to Bedrock format
        system_message = None
        conversation_messages = []
        
        for message in api_messages:
            if message["role"] == "system":
                system_message = message["content"]
            else:
                conversation_messages.append({
                    "role": message["role"],
                    "content": [{"type": "text", "text": message["content"]}]
                })
        
        # Prepare the request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": conversation_messages
        }
        
        # Add system message if present
        if system_message:
            request_body["system"] = system_message
        
        
        try:
            print(f"[Bedrock] Sending request to model: {self.bedrock_model_id}")
            print(f"[Bedrock] Request body: {json.dumps(request_body, indent=2)}")
            
            response = self.bedrock_client.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(request_body)
            )
            
            print(f"[Bedrock] Raw response type: {type(response)}")
            print(f"[Bedrock] Raw response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            print(f"[Bedrock] Raw response: {response}")
            
            # Parse the response
            response_body = json.loads(response["body"].read())
            print(f"[Bedrock] Parsed response body type: {type(response_body)}")
            print(f"[Bedrock] Parsed response body keys: {list(response_body.keys()) if isinstance(response_body, dict) else 'Not a dict'}")
            print(f"[Bedrock] Parsed response body: {json.dumps(response_body, indent=2)}")
            
            # Convert Bedrock response format to match OpenRouter format
            if "content" in response_body and len(response_body["content"]) > 0:
                print(f"[Bedrock] Content found, returning formatted response")
                return {
                    "choices": [{
                        "message": {
                            "content": response_body["content"][0]["text"]
                        }
                    }],
                    "usage": response_body.get("usage", {})
                }
            else:
                print(f"[Bedrock] No content found in response body")
                print(f"[Bedrock] Response body structure: {response_body}")
                raise Exception(f"Invalid response format from Bedrock. Response: {response_body}")
                
        except ClientError as e:
            print(f"[Bedrock] ClientError occurred: {e}")
            print(f"[Bedrock] Error response: {e.response}")
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            raise Exception(f"Bedrock API error [{error_code}]: {error_message}")
        except json.JSONDecodeError as e:
            print(f"[Bedrock] JSON decode error: {e}")
            print(f"[Bedrock] Raw response body that failed to parse: {response['body'].read()}")
            raise Exception(f"Invalid JSON response from Bedrock: {str(e)}")
        except Exception as e:
            print(f"[Bedrock] Unexpected error: {e}")
            print(f"[Bedrock] Error type: {type(e)}")
            import traceback
            print(f"[Bedrock] Full traceback: {traceback.format_exc()}")
            raise Exception(f"Bedrock request failed: {str(e)}")

    def extract_content(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and parse structured content from the LLM API response
        
        Args:
            api_response: The response from the LLM API
            
        Returns:
            Parsed content with code, next_steps, and is_deployable fields
        """
        try:
            # Both OpenRouter and Bedrock (converted) return response in choices[0].message.content format
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