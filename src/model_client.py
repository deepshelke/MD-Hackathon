"""
Hugging Face Inference API client for MedLlama-3.
Uses huggingface_hub InferenceClient (recommended approach).
"""
import os
import json
from typing import Dict, Optional, Any
import time

try:
    from huggingface_hub import InferenceClient
except ImportError:
    raise ImportError(
        "huggingface_hub not installed. Install with: pip install huggingface_hub"
    )


class HuggingFaceClient:
    """Client to interact with Hugging Face Inference API."""
    
    def __init__(self, 
                 model_name: str = "johnsnowlabs/JSL-MedLlama-3-8B-v2.0",
                 api_token: Optional[str] = None,
                 endpoint_url: Optional[str] = None):
        """
        Initialize Hugging Face client.
        
        Args:
            model_name: Model identifier on Hugging Face
            api_token: HF API token (or set HF_TOKEN env var)
            endpoint_url: Custom endpoint URL (if using Inference Endpoints)
                         If provided, model_name is ignored
        """
        self.model_name = model_name
        self.api_token = api_token or os.getenv("HF_TOKEN")
        
        if not self.api_token:
            raise ValueError(
                "Hugging Face API token required. "
                "Set HF_TOKEN env var or pass api_token parameter."
            )
        
        # Use custom endpoint if provided, otherwise use model name
        if endpoint_url:
            # Custom endpoint (Inference Endpoints)
            self.client = InferenceClient(model=endpoint_url, token=self.api_token)
        else:
            # Standard Inference API
            self.client = InferenceClient(model=model_name, token=self.api_token)
    
    def call_llm(self, 
                 system_prompt: str, 
                 user_prompt: str,
                 max_tokens: int = 900,
                 temperature: float = 0.2,
                 top_p: float = 0.95,
                 retry_count: int = 3,
                 retry_delay: int = 5) -> str:
        """
        Call the LLM via Hugging Face Inference API.
        
        Args:
            system_prompt: System prompt for the model
            user_prompt: User prompt with the note content
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (lower = more deterministic)
            top_p: Nucleus sampling parameter
            retry_count: Number of retries if request fails
            retry_delay: Seconds to wait between retries
            
        Returns:
            Generated text response from the model
        """
        # Combine system and user prompts
        # For text generation models, we format as a direct instruction
        # Format: "{system}\n\n{user}"
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        for attempt in range(retry_count):
            try:
                # Use InferenceClient for text generation
                response = self.client.text_generation(
                    prompt=full_prompt,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    return_full_text=False
                )
                
                return response.strip()
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Handle model loading (503 equivalent)
                if "loading" in error_str or "503" in error_str:
                    if attempt < retry_count - 1:
                        print(f"Model loading... waiting {retry_delay} seconds (attempt {attempt + 1}/{retry_count})")
                        time.sleep(retry_delay)
                        continue
                
                # Handle rate limiting (429 equivalent)
                if "429" in error_str or "rate limit" in error_str:
                    if attempt < retry_count - 1:
                        print(f"Rate limit exceeded. Waiting {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                
                # If last attempt, raise the error
                if attempt == retry_count - 1:
                    raise Exception(f"Failed to call Hugging Face API after {retry_count} attempts: {e}")
                
                # For other errors, wait and retry
                print(f"Request failed: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        
        raise Exception("Failed to get response from Hugging Face API")
    
    def simplify_note(self, 
                     system_prompt: str,
                     user_prompt: str,
                     **kwargs) -> str:
        """
        Simplify a medical note using the LLM.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt with note content
            **kwargs: Additional parameters for call_llm
            
        Returns:
            Simplified note as JSON string
        """
        return self.call_llm(system_prompt, user_prompt, **kwargs)

