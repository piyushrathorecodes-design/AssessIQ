import os
from app.config.settings import settings

def load_prompt(filename: str) -> str:
    """
    Loads a prompt template from the app/prompts directory.
    
    Args:
        filename: Name of the prompt file (e.g., 'system_prompt.txt')
        
    Returns:
        The content of the file as a string.
        
    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    path = os.path.join(settings.base_dir, settings.prompts_dir, filename)
    if not os.path.exists(path):
        # Fallback to local import check
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        if os.path.exists(local_path):
            path = local_path
        else:
            raise FileNotFoundError(f"Prompt template not found at: {path}")
            
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()
