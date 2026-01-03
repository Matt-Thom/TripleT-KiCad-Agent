import os
from litellm import completion
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self, model: str = "gpt-4o"):
        # Allow environment variable to override default model
        self.model = os.getenv("DEFAULT_AI_MODEL", model)

    async def get_response(self, messages: list):
        """
        Sends a list of messages to the LLM and returns the text response.
        Supports OpenAI, Anthropic, and Google Gemini via LiteLLM.
        """
        try:
            # LiteLLM handles the specific API calls for Gemini if the model name is 'gemini/...'
            response = completion(
                model=self.model,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"AI Service Error: {e}")
            return f"Error: I'm having trouble thinking right now. ({str(e)})"

ai_service = AIService()
