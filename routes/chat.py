from starlette.routing import Router, Route
from starlette.responses import JSONResponse
from services.chat_service import chat_service
from services.llm_service import llm_service
from services.auth_service import auth_service
from services.user_service import user_service
import json


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
        chat_session_id = body.get("chat_id")
        
        if not user_prompt:
            return JSONResponse(
                {"error": "Prompt is required"}, 
                status_code=400
            )
        
        # Get or create chat session
        if chat_session_id:
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
        if chat_session_id:
            result = llm_service.chat_with_assistant(messages, chat_session_id=chat_session_id)
        else:
            result = llm_service.chat_with_assistant(messages)
        print(f"LLM service response: {result}")
        # Extract the structured response
        structured_response = llm_service.extract_content(result)
        
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
        
        # Format messages for response
        messages_data = []
        for message in messages:
            messages_data.append({
                "id": message.id,
                "session_id": message.session_id,
                "role": message.role,
                "code": message.code,
                "next_steps": message.next_steps,
                "is_deployable": message.is_deployable,
                "content": message.content,
                "metadata": message.metadata,
                "created_at": message.created_at.isoformat() if message.created_at else None
            })
        
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


async def chat_handler(request):
    return JSONResponse({"status": "MCP Chat API"})


router = Router(routes=[
    Route("/create", chat, methods=["POST"]),
    Route("/sessions", get_user_sessions, methods=["GET"]),
    Route("/sessions/{session_id}/messages", get_session_messages, methods=["GET"]),
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

4. GET /chat/status - Get API status

curl -X GET http://localhost:8000/chat/status

"""

