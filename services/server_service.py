import re
from typing import Dict, Any, List
from services.server_db_service import ServerDatabaseService


class ServerService:
    """Business logic service for server operations"""
    
    @staticmethod
    def validate_create_server_data(data: Dict[str, Any]) -> List[str]:
        """Validate server creation data and return list of errors"""
        errors = []
        
        # Check required fields
        required_fields = ["name", "source_code", "wallet_address"]
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate name
        if "name" in data:
            name = data["name"].strip()
            if len(name) < 2:
                errors.append("Server name must be at least 2 characters long")
            if len(name) > 100:
                errors.append("Server name cannot exceed 100 characters")
        
        # Validate source_code
        if "source_code" in data:
            source_code = data["source_code"].strip()
            if len(source_code) < 10:
                errors.append("Source code is too short")
        
        # Validate wallet_address
        if "wallet_address" in data:
            wallet_address = data["wallet_address"].strip()
            if not wallet_address.startswith("0x") or len(wallet_address) != 42:
                errors.append("Invalid wallet address format")
        
        # Validate version format if provided
        if "version" in data and data["version"]:
            version = data["version"].strip()
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                errors.append("Version must be in format x.y.z (e.g., 1.0.0)")
        
        # Validate visibility
        if "visibility" in data and data["visibility"]:
            if data["visibility"] not in ["private", "public"]:
                errors.append("Visibility must be either 'private' or 'public'")
        
        # Validate tags
        if "tags" in data and data["tags"]:
            if not isinstance(data["tags"], list):
                errors.append("Tags must be an array")
            elif len(data["tags"]) > 10:
                errors.append("Cannot have more than 10 tags")
            else:
                for tag in data["tags"]:
                    if not isinstance(tag, str) or len(tag.strip()) == 0:
                        errors.append("All tags must be non-empty strings")
                        break
                    if len(tag) > 50:
                        errors.append("Tag length cannot exceed 50 characters")
                        break
        
        return errors
    
    @staticmethod
    def generate_slug(name: str) -> str:
        """Generate a URL-friendly slug from server name"""
        # Convert to lowercase and replace spaces/underscores with hyphens
        slug = name.lower().replace(" ", "-").replace("_", "-")
        
        # Remove any non-alphanumeric characters except hyphens
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # Ensure slug is not empty
        if not slug:
            slug = "server"
        
        # Ensure unique slug
        return ServerDatabaseService.generate_unique_slug(slug)
    
    @staticmethod
    def prepare_server_data(input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and sanitize server data for database insertion"""
        # Generate slug from name
        slug = ServerService.generate_slug(input_data["name"])
        
        # Prepare server data
        server_data = {
            "name": input_data["name"].strip(),
            "slug": slug,
            "source_code": input_data["source_code"].strip(),
            "wallet_address": input_data["wallet_address"].strip(),
            "description": input_data.get("description", "").strip(),
            "version": input_data.get("version", "1.0.0").strip(),
            "visibility": input_data.get("visibility", "private"),
            "category": input_data.get("category", "general").strip(),
            "status": "active"  # Set as active by default
        }
        
        # Handle tags
        if "tags" in input_data and input_data["tags"]:
            # Clean and deduplicate tags
            tags = list(set([tag.strip().lower() for tag in input_data["tags"] if tag.strip()]))
            server_data["tags"] = tags[:10]  # Limit to 10 tags
        
        return server_data
    
    @staticmethod
    def create_server(input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new server with validation and business logic"""
        # Validate input data
        errors = ServerService.validate_create_server_data(input_data)
        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")
        
        # Prepare server data
        server_data = ServerService.prepare_server_data(input_data)
        
        # Create server in database
        server_id = ServerDatabaseService.create_server(server_data)
        
        # Get and return the created server data
        created_server = ServerDatabaseService.get_server_by_id(server_id)
        if not created_server:
            raise RuntimeError("Failed to retrieve created server")
        
        return created_server