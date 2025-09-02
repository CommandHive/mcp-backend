from starlette.routing import Router, Route
from starlette.responses import JSONResponse
from services.chat_service import chat_service
from services.claude_code_service import claude_code_service
from services.llm_service import llm_service
from services.auth_service import auth_service
from services.user_service import user_service
from services.server_service import ServerService
from services.filesystem_service import filesystem_service
from mcp.server.fastmcp import FastMCP
import json
import inspect
import os
from pathlib import Path


def _is_response_complete(response):
    """Check if Claude Code response is complete"""
    content = response.get('content', '')
    
    if not content.strip():
        return False
    
    # Check for common completion indicators
    has_main_function = 'if __name__ == "__main__"' in content
    has_imports = any(line.strip().startswith('import') or line.strip().startswith('from') 
                     for line in content.split('\n'))
    has_fastmcp = 'FastMCP' in content
    
    return has_main_function and has_imports and has_fastmcp


def _validate_generated_code(code):
    """Validate that generated code is syntactically correct"""
    if not code.strip():
        return False
        
    try:
        compile(code, '<string>', 'exec')
        return True
    except SyntaxError:
        return False


def _is_code_deployable(code):
    """Check if code is ready for deployment"""
    if not code.strip():
        return False
        
    return (_validate_generated_code(code) and 
            'FastMCP' in code and 
            len(code.strip()) > 100)  # Minimum code length


def extract_tools_from_code(code: str, chat_session_id: str):
    """Extract tools from generated FastMCP code"""
    try:
        # Only expose FastMCP into exec env; block builtins from being mutated
        exec_globals = {"FastMCP": FastMCP}
        exec(code, exec_globals)

        tools = []
        print(f"Variables in exec_globals: {list(exec_globals.keys())}")

        # Find all FastMCP instances created by the code
        mcp_instances = []
        for name, value in exec_globals.items():
            if isinstance(value, FastMCP):
                print(f"Found FastMCP instance: {name}")
                mcp_instances.append((name, value))

        if not mcp_instances:
            print("No FastMCP instances found in executed code.")
            return tools

        # Extract tools from each FastMCP instance
        for inst_name, mcp_server in mcp_instances:
            tool_manager = getattr(mcp_server, "_tool_manager", None)
            if tool_manager is None:
                print(f"{inst_name} has no _tool_manager")
                continue

            raw_tools = getattr(tool_manager, "_tools", None)
            if not isinstance(raw_tools, dict):
                print(f"{inst_name} _tool_manager has no _tools dict")
                continue

            print(raw_tools)
            print(f"Tools in instance: {list(raw_tools.keys()) if raw_tools else []}")

            for tool_name, tool_obj in raw_tools.items():
                # Safely pull fields from FastMCP Tool wrapper
                fn_meta = getattr(tool_obj, "fn_metadata", None)
                output_schema = getattr(fn_meta, "output_schema", None) if fn_meta else None

                tools.append({
                    "instance": inst_name,
                    "name": getattr(tool_obj, "name", tool_name) or tool_name,
                    "description": getattr(tool_obj, "description", "") or "",
                    "parameters": getattr(tool_obj, "parameters", None),
                    "is_async": bool(getattr(tool_obj, "is_async", False)),
                    "output_schema": output_schema,
                })

        print(f"Extracted {len(tools)} tools: {[t['name'] for t in tools]}")
        return tools

    except Exception as e:
        print(f"Error extracting tools: {e}")
        import traceback
        traceback.print_exc()
        return []


async def execute_tool(request):
    """Execute a tool from a chat session's generated code"""
    try:
        # Get authenticated user
        if not hasattr(request.state, 'user') or not request.state.user:
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        
        chat_id = request.path_params.get("chat_id")
        tool_name = request.path_params.get("tool_name")
        body = await request.json()
        parameters = body.get("parameters", {})
        
        # Get the chat session to find associated server
        chat_session = chat_service.get_chat_session(chat_id)
        if not chat_session:
            return JSONResponse({"error": "Chat session not found"}, status_code=404)
        
        # Look for generated server files in session directory
        session_dir = Path("mcp_servers") / chat_id
        if not session_dir.exists():
            return JSONResponse({"error": "No server files found in this chat"}, status_code=404)
        
        # Read files from session directory
        files = filesystem_service.read_server_files(str(session_dir))
        if not files:
            return JSONResponse({"error": "No server files found in this chat"}, status_code=404)
        
        # Find main.py for execution
        main_file = None
        for file_data in files:
            if file_data['filename'] == 'main.py':
                main_file = file_data
                break
        
        if not main_file:
            return JSONResponse({"error": "No main.py found in chat session"}, status_code=404)
        
        latest_code = main_file['content']
        
        # Execute the code and find the tool
        try:
            exec_globals = {"FastMCP": FastMCP}
            exec(latest_code, exec_globals)
            
            tool_func = None
            
            # Find FastMCP instance first
            for value in exec_globals.values():
                if isinstance(value, FastMCP):
                    if hasattr(value, '_tool_manager') and hasattr(value._tool_manager, '_tools'):
                        if tool_name in value._tool_manager._tools:
                            tool_func = value._tool_manager._tools[tool_name].fn
                            break
            
            # If not found in FastMCP, look for standalone function
            if not tool_func:
                if tool_name in exec_globals and callable(exec_globals[tool_name]):
                    tool_func = exec_globals[tool_name]
            
            if not tool_func:
                return JSONResponse({"error": f"Tool '{tool_name}' not found"}, status_code=404)
            
            # Execute the tool with parameters
            result = tool_func(**parameters)
            
            return JSONResponse({
                "success": True,
                "result": result,
                "tool_name": tool_name,
                "parameters": parameters
            })
            
        except Exception as e:
            return JSONResponse({
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name
            }, status_code=400)
        
    except Exception as e:
        return JSONResponse({"error": f"Internal server error: {str(e)}"}, status_code=500)


async def chat(request):
    print(await request.json())
    try:
        # Get authenticated user from middleware
        if not hasattr(request.state, 'user') or not request.state.user:
            return JSONResponse(
                {"error": "Authentication required"}, 
                status_code=401
            )
        
        user_data = request.state.user
        user_id = user_data["id"]  # Use actual user.id instead of email
        body = await request.json()
        
        user_prompt = body.get("prompt", "")
        chat_session_id = body.get("chat_id", None)
        provider = body.get("provider", "bedrock")  # Default to openrouter
        
        if not user_prompt:
            return JSONResponse(
                {"error": "Prompt is required"}, 
                status_code=400
            )
        
        # Get or create chat session
        is_new_session = chat_session_id is None
        if chat_session_id is not None:
            chat_session = chat_service.get_chat_session(chat_session_id)
            if not chat_session:
                return JSONResponse(
                    {"error": "Chat session not found"}, 
                    status_code=404
                )
        else:
            # Create new chat session
            chat_session = chat_service.create_chat_session(
                user_id=user_id,
                title="MCP Server Chat"
            )
            chat_session_id = chat_session.id
        
        # Get conversation history
        conversation_history = chat_service.get_conversation_history(chat_session_id)
        print(f"Conversation history: {conversation_history}")
        # Format messages for API
        messages = llm_service.format_messages_for_api(conversation_history)
        print(f"Formatted messages: {messages}")
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        # Save user message to database
        chat_service.add_message(chat_session_id, "user", user_prompt)
        
        # Create working directory for this session
        working_dir = None
        if is_new_session:
            # For new sessions, create a temporary working directory
            session_dir = Path("mcp_servers") / chat_session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            working_dir = str(session_dir)
        
        # Make request to Claude Code SDK
        print(f"Sending messages to Claude Code SDK: {messages}")
        
        if is_new_session:
            # Generate MCP server for new sessions
            user_prompt = messages[-1]['content'] if messages else ""
            result = await claude_code_service.generate_mcp_server(user_prompt, working_dir)
        else:
            # Continue chat for existing sessions
            result = await claude_code_service.chat_with_claude(messages, working_dir, is_new_session)
        
        print(f"Claude Code SDK response: {result}")
        
        # Wait for complete response with validation
        max_retries = 3
        retry_count = 0
        
        # Continue collecting response until complete
        while retry_count < max_retries and result.get('success'):
            if _is_response_complete(result):
                break
                
            # Check if more content is available
            if result.get('has_more_content', False):
                try:
                    # Continue collecting response
                    additional_result = await claude_code_service.continue_generation(
                        chat_session_id, result.get('context', {})
                    )
                    
                    if additional_result.get('success'):
                        # Merge responses
                        existing_content = result.get('content', '')
                        new_content = additional_result.get('content', '')
                        result['content'] = existing_content + new_content
                        
                        # Update other fields
                        result.update({
                            'next_steps': additional_result.get('next_steps', result.get('next_steps')),
                            'is_deployable': additional_result.get('is_deployable', result.get('is_deployable')),
                            'context': additional_result.get('context', result.get('context'))
                        })
                    else:
                        break
                        
                except Exception as e:
                    print(f"Error continuing generation: {e}")
                    break
            else:
                break
                
            retry_count += 1

        # Structure response for compatibility with validation
        if result.get('success'):
            code_content = result.get('content', '')
            
            structured_response = {
                "code": code_content,
                "next_steps": result.get('next_steps', 'Review and deploy the server'),
                "is_deployable": _is_code_deployable(code_content) and result.get('is_deployable', False)
            }
        else:
            structured_response = {
                "code": "",
                "next_steps": f"Error: {result.get('error', 'Unknown error')}",
                "is_deployable": False
            }
        # Extract tools from generated code if it exists
        tools_preview = []
        if structured_response.get("code") and structured_response.get("code").strip():
            tools_preview = extract_tools_from_code(structured_response.get("code"), chat_session_id)
        
        # Extract tools from generated code if it exists
        tools_preview = []
        if structured_response.get("code") and structured_response.get("code").strip():
            tools_preview = extract_tools_from_code(structured_response.get("code"), chat_session_id)
        
        # Save assistant response to database (store the full structured response)
        chat_service.add_message(
            session_id=chat_session_id,
            role="assistant",
            content=json.dumps(structured_response),
            code=structured_response.get("code"),
            next_steps=structured_response.get("next_steps"),
            is_deployable=structured_response.get("is_deployable")
  )
        
        # Update session timestamp
        chat_service.update_session_timestamp(chat_session_id)
        
        return JSONResponse({
            "chat_session_id": chat_session_id,
            "code": structured_response.get("code", ""),
            "next_steps": structured_response.get("next_steps", ""),
            "is_deployable": structured_response.get("is_deployable", False),
            "tools": tools_preview,
            "inference_id": result.get("inference_id"),
            "episode_id": result.get("episode_id"),
            "usage": result.get("usage"),
            "success": True
        })
        
    except json.JSONDecodeError:
        return JSONResponse(
            {"error": "Invalid JSON in request body"}, 
            status_code=400
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"Internal server error: {str(e)}"}, 
            status_code=500
        )


async def get_user_sessions(request):
    """Get all chat sessions for the authenticated user"""
    try:
        # Extract and validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"success": False, "error": "Missing or invalid authorization header"},
                status_code=401
            )
        
        token = auth_header.split(" ")[1]
        payload = auth_service.verify_token(token)
        
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Invalid or expired token"},
                status_code=401
            )
        
        # Get email from token
        email = payload.get("sub")
        if not email:
            return JSONResponse(
                {"success": False, "error": "Invalid token payload"},
                status_code=401
            )
        
        # Get user from database to get wallet_address
        user = await user_service.get_user_by_email(email)
        if not user:
            return JSONResponse(
                {"success": False, "error": "User not found"},
                status_code=404
            )
        
        # Use user.id (UUID) as the identifier
        user_id = user.id
        
        # Get chat sessions for user
        sessions = chat_service.get_user_chat_sessions(user_id)
        
        # Format sessions for response
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                "id": session.id,
                "title": session.title,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None
            })
        
        return JSONResponse({
            "success": True,
            "sessions": sessions_data,
            "total": len(sessions_data)
        })
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": "Failed to get chat sessions"},
            status_code=500
        )


async def get_session_messages(request):
    """Get all messages for a specific chat session"""
    try:
        # Get authenticated user from middleware
        if not hasattr(request.state, 'user') or not request.state.user:
            return JSONResponse(
                {"error": "Authentication required"}, 
                status_code=401
            )
        
        user_data = request.state.user
        user_id = user_data["id"]
        
        # Get session_id from path parameters
        session_id = request.path_params.get("session_id")
        if not session_id:
            return JSONResponse(
                {"error": "Session ID is required"}, 
                status_code=400
            )
        
        # Verify that the session belongs to the authenticated user
        chat_session = chat_service.get_chat_session(session_id)
        if not chat_session:
            return JSONResponse(
                {"error": "Chat session not found"}, 
                status_code=404
            )
        
        if chat_session.user_id != user_id:
            return JSONResponse(
                {"error": "Access denied to this chat session"}, 
                status_code=403
            )
        
        # Get all messages for the session
        messages = chat_service.get_conversation_history(session_id)
        
        # Format messages for response and extract tools from assistant messages with code
        messages_data = []
        for message in messages:
            message_data = {
                "id": message.id,
                "session_id": message.session_id,
                "role": message.role,
                "code": message.code,
                "next_steps": message.next_steps,
                "is_deployable": message.is_deployable,
                "content": message.content,
                "metadata": message.metadata,
                "created_at": message.created_at.isoformat() if message.created_at else None
            }
            
            # Extract tools from assistant messages that have code
            if message.role == "assistant" and message.code and message.code.strip():
                tools = extract_tools_from_code(message.code, session_id)
                message_data["tools"] = tools
            
            messages_data.append(message_data)
        
        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "messages": messages_data,
            "total": len(messages_data)
        })
        
    except Exception as e:
        return JSONResponse(
            {"error": "Failed to get session messages"}, 
            status_code=500
        )


async def get_chat_files(request):
    """Get all files from a chat session's generated code"""
    try:
        # Get authenticated user
        if not hasattr(request.state, 'user') or not request.state.user:
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        
        chat_id = request.path_params.get("chat_id")
        
        # Get the chat session to verify ownership
        chat_session = chat_service.get_chat_session(chat_id)
        if not chat_session:
            return JSONResponse({"error": "Chat session not found"}, status_code=404)
        
        # Look for generated server files in session directory
        session_dir = Path("mcp_servers") / chat_id
        if not session_dir.exists():
            return JSONResponse({"success": True, "files": []})
        
        # Read files from session directory
        files = filesystem_service.read_server_files(str(session_dir))
        
        # Convert files to tree structure
        file_tree = _build_file_tree(files)
        
        return JSONResponse({
            "success": True,
            "files": file_tree,
            "total": len(files)
        })
        
    except Exception as e:
        return JSONResponse({"error": f"Internal server error: {str(e)}"}, status_code=500)


def _build_file_tree(files):
    """Convert flat file list to nested tree structure"""
    tree = []
    
    for file_data in files:
        path_parts = file_data['filename'].split('/')
        current_level = tree
        
        # Build nested structure
        for i, part in enumerate(path_parts):
            if i == len(path_parts) - 1:  # This is a file
                current_level.append({
                    "name": part,
                    "type": "file",
                    "path": file_data['filename'],
                    "content": file_data['content']
                })
            else:  # This is a folder
                # Look for existing folder
                folder = next((item for item in current_level if item["name"] == part and item["type"] == "folder"), None)
                if not folder:
                    folder = {
                        "name": part,
                        "type": "folder",
                        "path": '/'.join(path_parts[:i+1]),
                        "children": []
                    }
                    current_level.append(folder)
                current_level = folder["children"]
    
    return tree


async def get_chat_file_content(request):
    """Get specific file content from a chat session"""
    try:
        # Get authenticated user
        if not hasattr(request.state, 'user') or not request.state.user:
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        
        chat_id = request.path_params.get("chat_id")
        file_path = request.path_params.get("file_path")
        
        # Get the chat session to verify ownership
        chat_session = chat_service.get_chat_session(chat_id)
        if not chat_session:
            return JSONResponse({"error": "Chat session not found"}, status_code=404)
        
        # Look for the specific file
        session_dir = Path("mcp_servers") / chat_id
        if not session_dir.exists():
            return JSONResponse({"error": "No files found in this chat session"}, status_code=404)
        
        # Read the specific file
        target_file = session_dir / file_path
        if not target_file.exists() or not target_file.is_file():
            return JSONResponse({"error": "File not found"}, status_code=404)
        
        # Security check: ensure file is within session directory
        try:
            target_file.resolve().relative_to(session_dir.resolve())
        except ValueError:
            return JSONResponse({"error": "Access denied"}, status_code=403)
        
        try:
            content = target_file.read_text(encoding='utf-8')
            return JSONResponse({
                "success": True,
                "filename": file_path,
                "content": content,
                "file_type": filesystem_service._get_file_type(target_file.suffix)
            })
        except Exception as e:
            return JSONResponse({"error": f"Error reading file: {str(e)}"}, status_code=500)
        
    except Exception as e:
        return JSONResponse({"error": f"Internal server error: {str(e)}"}, status_code=500)


async def update_chat_file(request):
    """Update file content in a chat session"""
    try:
        # Get authenticated user
        if not hasattr(request.state, 'user') or not request.state.user:
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        
        chat_id = request.path_params.get("chat_id")
        file_path = request.path_params.get("file_path")
        body = await request.json()
        new_content = body.get("content", "")
        
        # Get the chat session to verify ownership
        chat_session = chat_service.get_chat_session(chat_id)
        if not chat_session:
            return JSONResponse({"error": "Chat session not found"}, status_code=404)
        
        # Look for the specific file
        session_dir = Path("mcp_servers") / chat_id
        if not session_dir.exists():
            return JSONResponse({"error": "No files found in this chat session"}, status_code=404)
        
        # Target file path
        target_file = session_dir / file_path
        
        # Security check: ensure file is within session directory
        try:
            target_file.resolve().relative_to(session_dir.resolve())
        except ValueError:
            return JSONResponse({"error": "Access denied"}, status_code=403)
        
        # Create directory if it doesn't exist
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Write the updated content
            target_file.write_text(new_content, encoding='utf-8')
            
            return JSONResponse({
                "success": True,
                "message": "File updated successfully",
                "filename": file_path
            })
        except Exception as e:
            return JSONResponse({"error": f"Error updating file: {str(e)}"}, status_code=500)
        
    except Exception as e:
        return JSONResponse({"error": f"Internal server error: {str(e)}"}, status_code=500)


async def deploy_chat_server(request):
    """Deploy MCP server from chat session's generated code"""
    try:
        # Get authenticated user
        if not hasattr(request.state, 'user') or not request.state.user:
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        
        user_data = request.state.user
        user_id = user_data["id"]
        wallet_address = user_data.get("wallet_address", "0x0000000000000000000000000000000000000000")
        
        chat_id = request.path_params.get("chat_id")
        body = await request.json()
        
        # Check if chat session has deployable server files
        session_dir = Path("mcp_servers") / chat_id
        if not session_dir.exists():
            return JSONResponse({"error": "No server files found in this chat session"}, status_code=404)
        
        # Check for main.py file (required for deployment)
        main_file = session_dir / "main.py"
        if not main_file.exists():
            return JSONResponse({"error": "No deployable server found in this chat session"}, status_code=404)
        
        # Read all files for deployment
        files = filesystem_service.read_server_files(str(session_dir))
        if not files:
            return JSONResponse({"error": "No deployable code found in this chat session"}, status_code=404)
        
        # Extract server name and description from the session directory
        try:
            metadata_result = await claude_code_service.extract_server_metadata(str(session_dir))
            if metadata_result.get('success'):
                metadata = metadata_result['metadata']
                server_name = metadata.get("name") or f"MCP Server from Chat {chat_id}"
                description = metadata.get("description") or "Deployed MCP server from chat session"
            else:
                raise Exception(metadata_result.get('error', 'Failed to extract metadata'))
        except Exception as e:
            print(f"Failed to extract metadata from Claude Code SDK: {e}")
            # Fallback to request body or defaults
            server_name = body.get("name") or f"MCP Server from Chat {chat_id}"
            description = body.get("description") or "Deployed MCP server from chat session"
        
        # Verify chat session belongs to user
        chat_session = chat_service.get_chat_session(chat_id)
        if not chat_session or chat_session.user_id != user_id:
            return JSONResponse({"error": "Access denied to this chat session"}, status_code=403)
        
        # Prepare server data for creation
        server_data = {
            "name": server_name,
            "user_id": user_id,
            "files": files,  # Use files from session directory
            "description": description,
            "version": "1.0.0",
            "visibility": "private",
            "category": "chat-generated"
        }
        
        # Create the server using ServerService
        created_server = ServerService.create_server(server_data)
        
        return JSONResponse({
            "success": True,
            "message": "MCP server deployed successfully",
            "server": created_server,
            "chat_id": chat_id
        }, status_code=201)
        
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"Deployment failed: {str(e)}"}, status_code=500)


async def chat_handler(request):
    return JSONResponse({"status": "MCP Chat API"})


router = Router(routes=[
    Route("/create", chat, methods=["POST"]),
    Route("/sessions", get_user_sessions, methods=["GET"]),
    Route("/sessions/{session_id}/messages", get_session_messages, methods=["GET"]),
    Route("/{chat_id}/files", get_chat_files, methods=["GET"]),
    Route("/{chat_id}/files/{file_path:path}", get_chat_file_content, methods=["GET"]),
    Route("/{chat_id}/files/{file_path:path}", update_chat_file, methods=["PUT"]),
    Route("/{chat_id}/tools/{tool_name}/execute", execute_tool, methods=["POST"]),
    Route("/{chat_id}/deploy", deploy_chat_server, methods=["POST"]),
    Route("/status", chat_handler, methods=["GET"])
])

"""
1. POST /chat/create - Create new chat or continue existing chat

curl -X POST http://localhost:8000/chat/create \
      -H "Content-Type: application/json" \
      -d '{
        "prompt": "Create an MCP server that can get weather information for any city",
        "user_id": "user_id_placeholder",
        "chat_session_id": "chat_session_id_placeholder (optional)"
      }'

2. GET /chat/sessions - Get all chat sessions for authenticated user

curl -X GET http://localhost:8000/chat/sessions \
      -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"

3. GET /chat/sessions/{session_id}/messages - Get all messages for a specific chat session

curl -X GET http://localhost:8000/chat/sessions/{session_id}/messages \
      -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"

4. POST /chat/{chat_id}/deploy - Deploy MCP server from chat session (name and description auto-generated from code)

curl -X POST http://localhost:8000/chat/{chat_id}/deploy \
      -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
      -H "Content-Type: application/json" \
      -d '{}'

5. GET /chat/status - Get API status

curl -X GET http://localhost:8000/chat/status

"""

