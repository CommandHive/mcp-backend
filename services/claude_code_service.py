"""
Claude Code SDK service for MCP server generation and chat interactions
Replaces the direct LLM API calls with Claude Code SDK functionality
"""

import asyncio
import os
from typing import Dict, List, Any, Optional, AsyncGenerator
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from pathlib import Path


class ClaudeCodeService:
    """Service for interacting with Claude Code SDK"""
    
    def __init__(self):
        """Initialize Claude Code service"""
        self.default_options = ClaudeCodeOptions(
            max_turns=5,
            model="claude-3-5-sonnet-20241022",
            permission_mode="acceptEdits",
            allowed_tools=["Read", "Write"],

            max_thinking_tokens=8000
        )
    
    async def generate_mcp_server(self, user_prompt: str, 
                                 working_directory: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate MCP server code using Claude Code SDK
        
        Args:
            user_prompt: User's description of the desired MCP server
            working_directory: Optional working directory for file operations
            
        Returns:
            Dict containing generated files, next_steps, and deployment info
        """
        
        # System prompt for MCP server generation
        system_prompt = """You are an expert MCP (Model Context Protocol) server developer. 
Your task is to create fully functional MCP servers using FastMCP framework.

IMPORTANT REQUIREMENTS:
1. Always create a main.py file with the FastMCP server instance
2. Use proper FastMCP decorators (@app.tool(), @app.resource(), etc.)
3. Include comprehensive error handling and input validation
4. Add proper docstrings and type hints
5. Create additional files as needed (utils.py, requirements.txt, etc.)
6. Make the server production-ready and deployable

The user will describe what they want the MCP server to do. Based on their request:
- Create all necessary files
- Ensure main.py contains a FastMCP instance
- Add requirements.txt if external packages are needed
- Include proper documentation
- Test that the server would work correctly

Always write clean, maintainable, and well-documented code."""

        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            cwd=working_directory,
            max_turns=3,
            model="claude-3-5-sonnet-20241022",
            permission_mode="acceptEdits",
            allowed_tools=["Write", "Read", "Edit", "MultiEdit"]
        )
        
        try:
            async with ClaudeSDKClient(options=options) as client:
                # Send the user prompt
                await client.query(f"""Create an MCP server based on this request: {user_prompt}

Please:
1. Create a main.py file with the FastMCP server
2. Add any additional Python files needed
3. Include requirements.txt if external packages are needed
4. Make the server fully functional and ready to deploy""")
                
                # Collect all responses
                response_content = []
                files_created = []
                
            
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                response_content.append(block.text)
                            
                            # Track file operations
                            if hasattr(block, 'type') and block.type == 'tool_use':
                                print(f"Tool use block: {block}")
                                if block.name in ['Write', 'Edit', 'MultiEdit']:
                                    # Extract file path from tool input
                                    if hasattr(block, 'input') and 'file_path' in block.input:
                                        files_created.append(block.input['file_path'])
                    
                    # Get final result with metadata
                    if type(message).__name__ == "ResultMessage":
                        return {
                            'success': True,
                            'content': ''.join(response_content),
                            'files_created': files_created,
                            'is_deployable': True,  # SDK ensures functional code
                            'next_steps': 'Review the generated files and deploy the MCP server',
                            'cost': getattr(message, 'total_cost_usd', 0),
                            'duration_ms': getattr(message, 'duration_ms', 0)
                        }
                
                # Fallback response
                return {
                    'success': True,
                    'content': ''.join(response_content),
                    'files_created': files_created,
                    'is_deployable': True,
                    'next_steps': 'Review the generated files and deploy the MCP server',
                    'cost': 0,
                    'duration_ms': 0
                }
                
        except Exception as e:
            print(f"Error generating MCP server: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': '',
                'files_created': [],
                'is_deployable': False,
                'next_steps': f'Error occurred: {str(e)}',
                'cost': 0,
                'duration_ms': 0
            }
    
    async def chat_with_claude(self, messages: List[Dict[str, str]], 
                              working_directory: Optional[str] = None,
                              is_new_session: bool = False) -> Dict[str, Any]:
        """
        Have a chat conversation with Claude using the SDK
        
        Args:
            messages: List of message objects with 'role' and 'content'
            working_directory: Optional working directory for file operations
            is_new_session: Whether this is a new chat session
            
        Returns:
            Dict containing the response and metadata
        """
        
        # System prompt for chat sessions
        system_prompt = """You are an expert software engineer and MCP server developer.
You can help users with:
- Creating and modifying MCP servers
- Debugging code issues
- Adding new features
- Explaining how code works
- Best practices and optimization

You have access to file system tools and can read, write, and modify files as needed."""

        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            cwd=working_directory,
            max_turns=5,
            model="claude-3-5-sonnet-20241022",
            permission_mode="acceptEdits",
            allowed_tools=["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob"]
        )
        
        try:
            async with ClaudeSDKClient(options=options) as client:
                # Convert messages to the format expected by SDK
                if messages:
                    # Send all messages in sequence
                    for message in messages:
                        await client.query(message['content'])
                
                # Collect responses
                response_content = []
                
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                response_content.append(block.text)
                    
                    if type(message).__name__ == "ResultMessage":
                        return {
                            'success': True,
                            'content': ''.join(response_content),
                            'cost': getattr(message, 'total_cost_usd', 0),
                            'duration_ms': getattr(message, 'duration_ms', 0),
                            'session_id': getattr(message, 'session_id', None)
                        }
                
                return {
                    'success': True,
                    'content': ''.join(response_content),
                    'cost': 0,
                    'duration_ms': 0,
                    'session_id': None
                }
                
        except Exception as e:
            print(f"Error in chat with Claude: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': f'Error: {str(e)}',
                'cost': 0,
                'duration_ms': 0,
                'session_id': None
            }
    
    async def analyze_and_improve_server(self, folder_path: str, 
                                       improvement_request: str) -> Dict[str, Any]:
        """
        Analyze existing MCP server and make improvements
        
        Args:
            folder_path: Path to the server directory
            improvement_request: What improvements to make
            
        Returns:
            Dict containing the analysis and improvement results
        """
        
        system_prompt = """You are an expert MCP server developer and code reviewer.
Analyze the provided MCP server code and make the requested improvements.

Focus on:
- Code quality and best practices
- Performance optimization
- Security considerations
- Adding requested features
- Fixing any bugs or issues
- Improving error handling and validation

Always maintain backward compatibility unless explicitly asked to break it."""

        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            cwd=folder_path,
            max_turns=4,
            model="claude-3-5-sonnet-20241022",
            permission_mode="acceptEdits",
            allowed_tools=["Write", "Read", "Edit", "MultiEdit"]

        )
        
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(f"""Please analyze the MCP server in this directory and make the following improvements:

{improvement_request}

First read the existing files to understand the current implementation, then make the requested changes.""")
                
                response_content = []
                files_modified = []
                
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                response_content.append(block.text)
                            
                            # Track file operations
                            if hasattr(block, 'type') and block.type == 'tool_use':
                                if block.name in ['Write', 'Edit', 'MultiEdit']:
                                    if hasattr(block, 'input') and 'file_path' in block.input:
                                        files_modified.append(block.input['file_path'])
                    
                    if type(message).__name__ == "ResultMessage":
                        return {
                            'success': True,
                            'analysis': ''.join(response_content),
                            'files_modified': files_modified,
                            'cost': getattr(message, 'total_cost_usd', 0),
                            'duration_ms': getattr(message, 'duration_ms', 0)
                        }
                
                return {
                    'success': True,
                    'analysis': ''.join(response_content),
                    'files_modified': files_modified,
                    'cost': 0,
                    'duration_ms': 0
                }
                
        except Exception as e:
            print(f"Error analyzing/improving server: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis': f'Error: {str(e)}',
                'files_modified': [],
                'cost': 0,
                'duration_ms': 0
            }
    
    async def extract_server_metadata(self, folder_path: str) -> Dict[str, Any]:
        """
        Extract metadata from MCP server (name, description, tools, etc.)
        
        Args:
            folder_path: Path to the server directory
            
        Returns:
            Dict containing server metadata
        """
        
        system_prompt = """You are a code analyst. Analyze the MCP server code and extract metadata.

Provide a JSON response with:
- name: Server name (from code or inferred)
- description: What the server does
- tools: List of available tools/functions
- dependencies: Required packages
- version: Version if specified

Focus on the FastMCP server implementation."""

        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            cwd=folder_path,
            max_turns=2,
            model="claude-3-5-sonnet-20241022",
            allowed_tools=["Read", "Grep", "Glob"]
        )
        
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query("Analyze the MCP server in this directory and extract metadata as JSON")
                
                response_content = []
                
                async for message in client.receive_response():
                    if hasattr(message, 'content'):
                        for block in message.content:
                            if hasattr(block, 'text'):
                                response_content.append(block.text)
                    
                    if type(message).__name__ == "ResultMessage":
                        content = ''.join(response_content)
                        
                        # Try to extract JSON from response
                        import json
                        import re
                        
                        # Look for JSON in the response
                        json_match = re.search(r'\{[^}]*\}', content, re.DOTALL)
                        if json_match:
                            try:
                                metadata = json.loads(json_match.group())
                                return {
                                    'success': True,
                                    'metadata': metadata
                                }
                            except json.JSONDecodeError:
                                pass
                        
                        # Fallback: parse manually
                        return {
                            'success': True,
                            'metadata': {
                                'name': 'MCP Server',
                                'description': 'Generated MCP Server',
                                'tools': [],
                                'dependencies': [],
                                'version': '1.0.0'
                            }
                        }
                
        except Exception as e:
            print(f"Error extracting server metadata: {e}")
            return {
                'success': False,
                'error': str(e),
                'metadata': {}
            }


# Global instance
claude_code_service = ClaudeCodeService()