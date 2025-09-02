import re
from typing import Dict, Any, List
from services.server_db_service import ServerDatabaseService
from services.filesystem_service import filesystem_service


class ServerService:
    """Business logic service for server operations"""
    
    @staticmethod
    def validate_create_server_data(data: Dict[str, Any]) -> List[str]:
        """Validate server creation data and return list of errors"""
        errors = []
        
        # Check for files (source_code is no longer supported)
        has_files = "files" in data and data["files"]
        
        if not has_files:
            errors.append("Must provide 'files' array with server files")
        
        # Check other required fields
        required_fields = ["name", "user_id"]
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate name
        if "name" in data and data["name"] is not None:
            name = data["name"].strip()
            if len(name) < 2:
                errors.append("Server name must be at least 2 characters long")
            if len(name) > 100:
                errors.append("Server name cannot exceed 100 characters")
        
        # Validate files if provided
        if has_files:
            files = data["files"]
            if not isinstance(files, list):
                errors.append("Files must be an array")
            elif len(files) == 0:
                errors.append("Files array cannot be empty")
            elif len(files) > 100:
                errors.append("Cannot have more than 100 files")
            else:
                # Check if main.py exists
                main_py_found = False
                filenames = set()
                
                for i, file_data in enumerate(files):
                    if not isinstance(file_data, dict):
                        errors.append(f"File {i} must be an object")
                        continue
                    
                    # Check required file fields
                    if "filename" not in file_data or not file_data["filename"]:
                        errors.append(f"File {i} missing required 'filename'")
                    if "content" not in file_data or not file_data["content"]:
                        errors.append(f"File {i} missing required 'content'")
                    
                    if "filename" in file_data:
                        filename = file_data["filename"].strip()
                        
                        # Check for duplicate filenames
                        if filename in filenames:
                            errors.append(f"Duplicate filename: {filename}")
                        filenames.add(filename)
                        
                        # Check if this is main.py
                        if filename == "main.py":
                            main_py_found = True
                        
                        # Validate filename
                        if not re.match(r'^[a-zA-Z0-9_/.-]+$', filename):
                            errors.append(f"Invalid filename: {filename}")
                        
                        # Prevent directory traversal
                        if ".." in filename or filename.startswith("/"):
                            errors.append(f"Invalid filename (security): {filename}")
                
                if not main_py_found:
                    errors.append("main.py file is required in files array")
        
        # Validate user_id (should be a valid UUID)
        if "user_id" in data and data["user_id"] is not None:
            try:
                import uuid
                uuid.UUID(str(data["user_id"]))
            except (ValueError, TypeError):
                errors.append("Invalid user_id format")
        
        # Validate version format if provided
        if "version" in data and data["version"] is not None:
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
            "name": (input_data["name"] or "").strip(),
            "slug": slug,
            "user_id": input_data["user_id"],
            "description": (input_data.get("description") or "").strip(),
            "version": (input_data.get("version") or "1.0.0").strip(),
            "visibility": input_data.get("visibility", "private"),
            "category": (input_data.get("category") or "general").strip(),
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
        
        # Create server in database (this will also create the folder)
        server_id = ServerDatabaseService.create_server(server_data)
        
        # Create files in the server directory
        if "files" in input_data and input_data["files"]:
            ServerDatabaseService.create_server_files(server_id, input_data["files"])
        
        # Get and return the created server data
        created_server = ServerDatabaseService.get_server_by_id(server_id)
        if not created_server:
            raise RuntimeError("Failed to retrieve created server")
        
        return created_server