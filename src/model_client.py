"""
Hugging Face Inference API client for MedLlama-3.
Uses huggingface_hub InferenceClient (recommended approach).
"""
import os
import json
import logging
from typing import Dict, Optional, Any
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from huggingface_hub import InferenceClient
except ImportError:
    raise ImportError(
        "huggingface_hub not installed. Install with: pip install huggingface_hub"
    )


class HuggingFaceClient:
    """Client to interact with Hugging Face Inference API."""
    
    def __init__(self,
                 ##where the model name is defined##
                 model_name: str = "google/medgemma-27b",
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
                 max_tokens: int = 2000,
                 temperature: float = 0.2,
                 top_p: float = 0.95,
                 retry_count: int = 1,  # Not used - only try once
                 retry_delay: int = 5) -> str:  # Not used - no retries
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
        # Log prompt details for debugging
        logger.info(f"📤 Sending prompt to model:")
        logger.info(f"   System prompt length: {len(system_prompt)} chars")
        logger.info(f"   User prompt length: {len(user_prompt)} chars")
        logger.info(f"   User prompt preview (first 500 chars): {user_prompt[:500]}")
        logger.info(f"   User prompt contains 'START OF MEDICAL DISCHARGE NOTE': {'START OF MEDICAL DISCHARGE NOTE' in user_prompt}")
        logger.info(f"   User prompt contains 'END OF MEDICAL DISCHARGE NOTE': {'END OF MEDICAL DISCHARGE NOTE' in user_prompt}")
        
        # Check if note sections are present in user prompt
        note_markers_found = user_prompt.count("=== START OF MEDICAL DISCHARGE NOTE ===")
        logger.info(f"   Note start markers found: {note_markers_found}")
        
        # Log a sample of the user prompt to see if sections are populated
        if "HISTORY OF PRESENT ILLNESS:" in user_prompt:
            hpi_start = user_prompt.find("HISTORY OF PRESENT ILLNESS:")
            hpi_end = min(hpi_start + 200, len(user_prompt))
            logger.info(f"   HPI section sample: {user_prompt[hpi_start:hpi_end]}")
        
        # Only try once - no retries to avoid wasting credits
        try:
            # Format prompt using Llama 3 chat template format
            # MedLlama-3 expects this exact format with special tokens
            combined_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>
{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""
            
            logger.info(f"🔄 Calling Hugging Face API...")
            logger.info(f"   Model: {self.model_name}")
            logger.info(f"   Max tokens: {max_tokens}")
            logger.info(f"   Temperature: {temperature}")
            logger.info(f"   Combined prompt length: {len(combined_prompt)} chars")
            logger.info(f"   Using Llama 3 chat template format")
            
            response = self.client.text_generation(
                prompt=combined_prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                return_full_text=False
            )
            
            # Convert to string if needed
            if response is None:
                response = ""
            else:
                response = str(response)
            
            # Check response type and content
            response_type = type(response).__name__
            response_length = len(response) if response else 0
            
            logger.info(f"📥 Received response:")
            logger.info(f"   Response type: {response_type}")
            logger.info(f"   Response length: {response_length} chars")
            logger.info(f"   Response preview (first 500 chars): {response[:500] if response else 'EMPTY'}")
            
            # If empty response, provide detailed error
            if not response or len(response.strip()) == 0:
                raise Exception(f"Empty response from LLM (type: {response_type}, length: {response_length}) - API call succeeded but model returned no output")
            
            return response.strip()
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Handle payment required (402) - fail immediately
            if "402" in error_str or "payment" in error_str:
                raise Exception("API requires payment - free tier limit reached")
            
            # Handle permission errors (403)
            if "403" in error_str or "forbidden" in error_str or "permission" in error_str:
                raise Exception("API permission denied - token needs Inference Providers permission")
            
            # For all other errors, fail immediately (no retries)
            raise Exception(f"Failed to call Hugging Face API: {e}")
    
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

