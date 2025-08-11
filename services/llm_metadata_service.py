import requests
import json
import os
import re
from typing import Dict, Any
from prompts.constants import (
    METADATA_EXTRACTION_SYSTEM_PROMPT,
    METADATA_EXTRACTION_USER_PROMPT
)


class LLMMetadataService:
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

    def extract_name_and_description(self, code: str) -> Dict[str, str]:
        """
        Extract name and description from generated MCP server code using LLM
        
        Args:
            code: The generated MCP server code
            
        Returns:
            Dict containing 'name' and 'description' keys
        """
        
        system_prompt = METADATA_EXTRACTION_SYSTEM_PROMPT

        messages = [
            {
                "role": "system", 
                "content": system_prompt
            },
            {
                "role": "user",
                "content": METADATA_EXTRACTION_USER_PROMPT.format(code=code)
            }
        ]
        
        payload = {
            "model": self.model,
            "messages": messages
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
            
            api_response = response.json()
            return self._parse_metadata_response(api_response)
            
        except Exception as e:
            print(f"Error extracting metadata: {str(e)}")
            raise

    def _parse_metadata_response(self, api_response: Dict[str, Any]) -> Dict[str, str]:
        """
        Parse the LLM response to extract name and description
        
        Args:
            api_response: The response from the OpenRouter API
            
        Returns:
            Dict containing name and description
        """
        if "choices" in api_response and len(api_response["choices"]) > 0:
            choice = api_response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
                
                # Extract name
                name_match = re.search(r'<name>(.*?)</name>', content, re.DOTALL)
                name = name_match.group(1).strip() if name_match else None
                
                # Extract description
                description_match = re.search(r'<description>(.*?)</description>', content, re.DOTALL)
                description = description_match.group(1).strip() if description_match else None
                
                if name and description:
                    return {
                        "name": name,
                        "description": description
                    }
        
        raise Exception("Failed to extract name and description from LLM response")


llm_metadata_service = LLMMetadataService()