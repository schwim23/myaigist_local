import os
from .ollama_client import get_ollama_client

class Summarizer:
    """Agent responsible for text summarization with multiple detail levels using Ollama"""

    def __init__(self):
        self.client = get_ollama_client()
        self.model = os.getenv('OLLAMA_MODEL', 'qwen2.5:14b')
        
        # Define summary configurations for different detail levels
        self.summary_configs = {
            'quick': {
                'max_tokens': 300,
                'system_prompt': """You are an expert summarizer. Create a quick, concise summary with 2-3 key bullet points.
                Focus only on the most essential information. Keep it brief and actionable.""",
                'user_prompt': "Provide a quick summary with 2-3 key bullet points of the most important information:",
                'description': "Quick overview with 2-3 key points"
            },
            'standard': {
                'max_tokens': 600,
                'system_prompt': """You are an expert summarizer. Create a balanced summary with 4-5 main topics.
                Include key details and context while maintaining readability. This is the default level.""",
                'user_prompt': "Provide a standard summary covering the main topics and key details:",
                'description': "Balanced summary with main topics and details"
            },
            'detailed': {
                'max_tokens': 1200,
                'system_prompt': """You are an expert summarizer. Create a comprehensive analysis with detailed insights.
                Organize information into 6+ sections with context, implications, and deeper analysis.""",
                'user_prompt': "Provide a detailed, comprehensive summary with analysis, context, and implications:",
                'description': "Comprehensive analysis with context and insights"
            }
        }

    def summarize(self, text: str, detail_level: str = 'standard') -> str:
        """
        Summarize text with specified detail level
        
        Args:
            text (str): Text to summarize
            detail_level (str): Summary level - 'quick', 'standard', or 'detailed'
            
        Returns:
            str: Generated summary
        """
        # Validate and set default detail level
        if detail_level not in self.summary_configs:
            detail_level = 'standard'
            
        config = self.summary_configs[detail_level]
        
        # Handle empty or very short text
        if not text or len(text.strip()) < 50:
            return "Text is too short to summarize meaningfully."
        
        # Truncate very long text to avoid token limits
        max_input_chars = 12000  # Rough estimate for token limits
        if len(text) > max_input_chars:
            text = text[:max_input_chars] + "..."
        
        try:
            # Use Ollama chat API
            messages = [
                {
                    "role": "system",
                    "content": config['system_prompt']
                },
                {
                    "role": "user",
                    "content": f"{config['user_prompt']}\n\n{text}"
                }
            ]

            summary = self.client.chat(
                messages=messages,
                temperature=0.7,
                top_p=0.9
            ).strip()
            
            # Add summary level indicator
            level_indicator = f"[{detail_level.upper()} SUMMARY]\n\n"
            return level_indicator + summary
            
        except Exception as e:
            error_msg = f"Error generating {detail_level} summary: {str(e)}"
            print(f"❌ Summarizer error: {error_msg}")
            return error_msg

    def get_available_levels(self) -> dict:
        """
        Get available summary levels and their descriptions
        
        Returns:
            dict: Dictionary of level names and descriptions
        """
        return {level: config['description'] for level, config in self.summary_configs.items()}

    def get_level_info(self, level: str) -> dict:
        """
        Get information about a specific summary level
        
        Args:
            level (str): Summary level name
            
        Returns:
            dict: Level configuration info
        """
        if level in self.summary_configs:
            config = self.summary_configs[level]
            return {
                'level': level,
                'description': config['description'],
                'max_tokens': config['max_tokens']
            }
        return None