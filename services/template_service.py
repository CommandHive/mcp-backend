import shutil
from pathlib import Path


class TemplateService:
    """Service for copying template files to new chat sessions."""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates"
    
    def copy_templates_to_session(self, session_dir: str) -> bool:
        """Copy all template files to a new chat session directory."""
        try:
            session_path = Path(session_dir)
            session_path.mkdir(parents=True, exist_ok=True)
            
            if not self.templates_dir.exists():
                print(f"Templates directory not found: {self.templates_dir}")
                return False
            
            # Copy all files from templates to session directory
            for item in self.templates_dir.iterdir():
                if item.is_file():
                    dest_file = session_path / item.name
                    shutil.copy2(item, dest_file)
                    print(f"Copied template: {item.name}")
                elif item.is_dir():
                    dest_dir = session_path / item.name
                    shutil.copytree(item, dest_dir, dirs_exist_ok=True)
                    print(f"Copied template directory: {item.name}")
            
            print(f"Successfully copied templates to: {session_dir}")
            return True
            
        except Exception as e:
            print(f"Error copying templates: {e}")
            return False


# Create singleton instance
template_service = TemplateService()