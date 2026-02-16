import requests
import logging
import os
import json

class LLMInterface:
    def __init__(self, config):
        # We use the Groq key (gsk_...) and the Groq endpoint
        self.api_key = os.getenv("GROK_API_KEY") 
        # Verified Groq Endpoint
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        # Best model for Groq coding tasks
        self.model = "llama-3.3-70b-versatile" 

    def _call_llm(self, messages, temperature=0.2):
        if not self.api_key:
            return "Error: API Key not found in environment variables."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        try:
            # We use .post() - Groq will reject .get() calls to this URL
            response = requests.post(
                self.api_url, 
                headers=headers, 
                json=payload, 
                timeout=45 
            )
            
            if response.status_code != 200:
                logging.error(f"Groq API Error: {response.status_code} - {response.text}")
                return f"API Error: {response.status_code}. Ensure your key is valid for Groq."

            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            logging.error(f"Unexpected Connection Error: {e}")
            return f"Failed to reach LLM: {str(e)}"

    def get_suggestion(self, prompt_type, code, context=''):        
        system_prompts = {
            'refactor': "You are a Senior Software Architect. Suggest improvements for readability and performance.",
            'explain': "You are a Lead Developer. Explain this code clearly to a junior teammate.",
            'bugfix': "You are a Security Researcher. Identify bugs, security flaws, or edge cases.",
            'generate': "You are a Python Expert. Complete the request with clean, idiomatic code."
        }
        
        system_msg = system_prompts.get(prompt_type, "You are a helpful coding assistant.")
        user_content = f"CONTEXT:\n{context}\n\nCODE:\n```python\n{code}\n```"
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content}
        ]
        
        return self._call_llm(messages)

    def suggest_test_fixes(self, test_output):
        messages = [
            {"role": "system", "content": "You are an expert debugger. Provide the exact fix for the test failure."},
            {"role": "user", "content": f"The tests failed with this output:\n\n{test_output}"}
        ]
        return self._call_llm(messages, temperature=0.1)