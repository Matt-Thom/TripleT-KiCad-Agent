import os
import json
from litellm import completion
from dotenv import load_dotenv
from backend.services.tools import tools, execute_tool

load_dotenv()

class AIService:
    # Service to handle AI interaction
    def __init__(self, model: str = "gpt-4o"):
        # Allow environment variable to override default model
        self.model = os.getenv("DEFAULT_AI_MODEL", model)

    async def get_response(self, messages: list):
        """
        Sends a list of messages to the LLM and handles tool calling loop.
        """
        try:
            # First Call: Check if the AI wants to use a tool
            response = completion(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # If no tool calls, just return the text
            if not tool_calls:
                return response_message.content

            # If tool calls exist, execute them
            messages.append(response_message) # Add the assistant's "intent" to history
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"AI Calling Tool: {function_name} with {function_args}")
                
                tool_result = await execute_tool(function_name, function_args)
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_result
                })

            # Second Call: Get the final answer based on tool results
            final_response = completion(
                model=self.model,
                messages=messages
            )
            return final_response.choices[0].message.content

        except Exception as e:
            print(f"AI Service Error: {e}")
            return f"Error: I'm having trouble thinking right now. Model: {self.model}. Error: {str(e)}"

ai_service = AIService()
