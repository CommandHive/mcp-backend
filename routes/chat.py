from starlette.routing import Router, Route
from starlette.responses import JSONResponse
from services.chat_service import chat_service
from services.llm_service import llm_service
from services.auth_service import auth_service
from services.user_service import user_service
from services.server_code_service import ServerCodeService
from services.server_service import ServerService
from services.llm_metadata_service import llm_metadata_service
from mcp.server.fastmcp import FastMCP
import json
import inspect


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
        
        # Get the latest code from chat session
        messages = chat_service.get_conversation_history(chat_id)
        latest_code = None
        
        for message in reversed(messages):
            if message.role == "assistant" and message.code:
                latest_code = message.code
                break
        
        if not latest_code:
            return JSONResponse({"error": "No executable code found in this chat"}, status_code=404)
        
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
        
        # Make request to LLM service
        print(f"Sending messages to LLM service with provider {provider}: {messages}")
        result = llm_service.chat_with_assistant(messages, chat_session_id=chat_session_id, is_new_session=is_new_session, provider=provider)
        print(f"LLM service response: {result}")
        # Extract the structured response
        structured_response = llm_service.extract_content(result)
        print(structured_response)
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
        
        # Get the latest deployable code from chat session
        messages = chat_service.get_conversation_history(chat_id)
        latest_code = None
        
        for message in reversed(messages):
            if message.role == "assistant" and message.code and message.is_deployable:
                latest_code = message.code
                break
        
        if not latest_code:
            return JSONResponse({"error": "No deployable code found in this chat session"}, status_code=404)
        
        # Get server name and description from LLM API based on the code
        try:
            metadata = llm_metadata_service.extract_name_and_description(latest_code)
            server_name = metadata.get("name") or f"MCP Server from Chat {chat_id}"
            description = metadata.get("description") or "Deployed MCP server from chat session"
        except Exception as e:
            print(f"Failed to extract metadata from LLM: {e}")
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
            "source_code": latest_code,
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

