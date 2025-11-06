"""
Heavy prompt engineering for MedLlama-3 to simplify discharge notes.
"""
from typing import Dict, Optional


class PromptBuilder:
    """Builds system and user prompts for medical note simplification."""
    
    SYSTEM_PROMPT = """You are a medical communication specialist. Simplify medical discharge notes into patient-friendly language at 6th-8th grade reading level.

Rules:
- Use ONLY information from the provided note
- Use simple, clear sentences (15-20 words max)
- Replace medical jargon with everyday language
- If information is missing, use "not specified"
- Be empathetic and reassuring"""

    USER_TEMPLATE = """Simplify this medical discharge note for a patient. Provide a clear summary, actions needed, medications explained, and a glossary of medical terms.

Medical Note:

[Diagnoses]
{diagnoses}

[Hospital Course]
{hospital_course}

[Discharge Medications]
{discharge_medications}

[Follow-up]
{followup}

[Allergies]
{allergies}

[Pending Tests]
{pending_tests}

[Diet/Activity]
{diet_activity}

Provide your response in this JSON format:
{{
  "summary": ["bullet 1", "bullet 2", "bullet 3"],
  "actions": [{{"task": "...", "when": "...", "who": "..."}}],
  "medications": [{{"name": "...", "why": "...", "how_to_take": "...", "schedule": "...", "cautions": "..."}}],
  "glossary": [{{"term": "...", "plain": "..."}}]
}}"""

    @staticmethod
    def build_user_prompt(sections: Dict[str, str]) -> str:
        """
        Build user prompt from sectionized note.
        
        Args:
            sections: Dictionary with keys: diagnoses, hospital_course, 
                    discharge_medications, followup, allergies, 
                    pending_tests, diet_activity
                    
        Returns:
            Formatted user prompt string
        """
        # Get values with fallback to "not specified"
        diagnoses = sections.get("Diagnoses", "not specified")
        hospital_course = sections.get("Hospital Course", "not specified")
        discharge_medications = sections.get("Discharge Medications", "not specified")
        followup = sections.get("Follow-up", "not specified")
        allergies = sections.get("Allergies", "not specified")
        pending_tests = sections.get("Pending Tests", "not specified")
        diet_activity = sections.get("Diet/Activity", "not specified")
        
        return PromptBuilder.USER_TEMPLATE.format(
            diagnoses=diagnoses,
            hospital_course=hospital_course,
            discharge_medications=discharge_medications,
            followup=followup,
            allergies=allergies,
            pending_tests=pending_tests,
            diet_activity=diet_activity
        )
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get the system prompt."""
        return PromptBuilder.SYSTEM_PROMPT
    
    @staticmethod
    def build_full_prompt(sections: Dict[str, str]) -> Dict[str, str]:
        """
        Build complete prompt (system + user) for LLM.
        
        Args:
            sections: Sectionized note dictionary
            
        Returns:
            Dictionary with 'system' and 'user' prompts
        """
        return {
            "system": PromptBuilder.get_system_prompt(),
            "user": PromptBuilder.build_user_prompt(sections)
        }

