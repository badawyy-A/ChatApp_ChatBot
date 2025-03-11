import requests
import time
import json
import os
from dotenv import load_dotenv

class GeminiAPI:
    def __init__(self):
        load_dotenv()
        self.api_keys = [
            os.environ.get(f"GEMINI_API_KEY_{i}") for i in range(1, 7)
        ]
        self.api_keys = [key for key in self.api_keys if key]
        
        if not self.api_keys:
            raise EnvironmentError("No Gemini API keys found in environment variables.")
    
    def _call_api_with_retry(self, url, headers, data, max_retries=3):
        """Retries API call in case of rate limits (429 errors)."""
        for attempt in range(max_retries):
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 429:  # Rate limit exceeded
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limit hit, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                return response.json()
        
        return None  # If all retries fail
    
    def get_report(self, input_prompt, model_name="models/gemini-1.5-pro"):
        """Generates a Gemini report using the specified model with API key rotation."""
        headers = {"Content-Type": "application/json"}
        data = {"contents": [{"parts": [{"text": input_prompt}]}]}
        
        for api_key in self.api_keys:  # Loop through API keys
            url = f"https://generativelanguage.googleapis.com/v1/{model_name}:generateContent?key={api_key}"
            
            try:
                response_json = self._call_api_with_retry(url, headers, data)
                if not response_json:
                    print(f"API key {api_key} failed. Trying next key...")
                    continue  # Try next API key
                
                print(f"Response JSON: {json.dumps(response_json, indent=2)}")
                
                text = response_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                
                return text if text else "Error: Text not found in response"
            
            except requests.exceptions.RequestException as e:
                print(f"Request Error with key {api_key}: {e}")
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error with key {api_key}: {e}")
            
            time.sleep(1)  # Delay before switching to the next key
        
        return "Error: All API keys failed"
