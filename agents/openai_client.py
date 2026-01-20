import os
from openai import OpenAI

def get_openai_client():
    """
    Get configured OpenAI client
    
    Returns:
        OpenAI: Configured OpenAI client instance
    """
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    return OpenAI(api_key=api_key)