import requests
import json
from typing import Optional

class AIClient:
    """
    Client for interacting with AI models through OpenRouter API.
    """
    
    def __init__(self):
        # Replace with your actual OpenRouter API key
        self.API_KEY = "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"
        self.API_URL = "https://openrouter.ai/api/v1/chat/completions"
        self.default_headers = {
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://jarvis-assistant.com",
            "X-Title": "JARVIS Assistant"
        }
        self.timeout = 10
        self.default_model = "deepseek/deepseek-r1:free"

    def ask_ai(
        self,
        question: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 200
    ) -> str:
        """
        Query AI model through OpenRouter API.
        """
        messages = [{"role": "user", "content": question}]

        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": min(max(temperature, 0), 2),
            "max_tokens": min(max(max_tokens, 50), 500)
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=self.default_headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return f"I'm having trouble connecting right now. Please try again."
                
            return response.json()["choices"][0]["message"]["content"]
            
        except requests.exceptions.Timeout:
            return "The AI is taking too long to respond. Please try a simpler question."
        except requests.exceptions.RequestException as e:
            return f"Connection error: Please check your internet connection."
        except (KeyError, json.JSONDecodeError) as e:
            return "Error processing the response. Please try again."
        except Exception as e:
            return "An unexpected error occurred. Please try again."


# Backward compatible function
def ask_ai(question: str) -> str:
    client = AIClient()
    return client.ask_ai(question)
