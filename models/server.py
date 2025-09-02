from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class Server(BaseModel):
    id: Optional[str] = None
    user_id: str
    name: str
    slug: str
    description: Optional[str] = None
    version: str = "1.0.0"
    status: str = "inactive"
    visibility: str = "private"
    folder_path: Optional[str] = None  # Path to server folder on filesystem
    package_json: Optional[Dict[str, Any]] = None
    environment_vars: Optional[Dict[str, str]] = None
    container_id: Optional[str] = None
    deployment_url: Optional[str] = None
    health_check_url: Optional[str] = None
    last_deployed_at: Optional[datetime] = None
    total_requests: int = 0
    last_accessed_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    is_featured: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ServerVersion(BaseModel):
    id: Optional[str] = None
    server_id: str
    version: str
    folder_path: Optional[str] = None  # Path to version folder on filesystem
    package_json: Optional[Dict[str, Any]] = None
    changelog: Optional[str] = None
    created_by: str
    created_at: Optional[datetime] = None


class ServerUsageLog(BaseModel):
    id: Optional[str] = None
    server_id: str
    tool_name: Optional[str] = None
    client_identifier: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_status: Optional[int] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None

    """rename wallet_address to user_id in Server"""
