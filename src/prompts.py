"""
Heavy prompt engineering for MedLlama-3 to simplify discharge notes.
"""
from typing import Dict, Optional

# Maximum prompt length (no hard limit - removed 7000 char restriction)
MAX_PROMPT_LENGTH = 10000  # Increased default, but trimming logic still works if needed


class PromptBuilder:
    """Builds system and user prompts for CareNotes - medical note simplification."""
    
    SYSTEM_PROMPT = """You are a medical communication specialist. Simplify medical discharge notes into patient-friendly language that anyone can understand.

Read the medical note below and explain it in simple, everyday words. Use the format specified in the user message."""

    USER_TEMPLATE = """Simplify this medical discharge note for a patient. Read the note below and explain everything in simple, everyday language.

IMPORTANT: Do NOT just copy the sections. SIMPLIFY and EXPLAIN each part in patient-friendly language.

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

[History of Present Illness]
{history_present_illness}

[Chief Complaint]
{chief_complaint}

[Past Medical History]
{past_medical_history}

[Physical Exam]
{physical_exam}

[Pertinent Results]
{pertinent_results}

[Discharge Instructions]
{discharge_instructions}

Now simplify this note. Provide your response in this format:

📋 Summary
- The patient was admitted to the hospital with [condition]. They were treated with [treatment]. They are being discharged [disposition].

✅ Actions Needed
- Take the prescribed medications as directed.
- Follow up with [provider] as scheduled.
- Monitor for any worsening symptoms and seek medical attention if necessary.

💊 Medications Explained
[Medication name]: [What it does and how to take it]
[Medication name]: [What it does and how to take it]

⚠️ Safety Information
[Allergies and warning signs in simple terms]

📖 Glossary
[Term]: [Simple definition]
[Term]: [Simple definition]"""

    @staticmethod
    def _trim_text(text: str, max_length: int) -> str:
        """Trim text to max_length, preserving word boundaries."""
        if len(text) <= max_length:
            return text
        # Trim to max_length and find last space
        trimmed = text[:max_length]
        last_space = trimmed.rfind(' ')
        if last_space > max_length * 0.8:  # If we found a space in last 20%
            return trimmed[:last_space] + "..."
        return trimmed + "..."
    
    @staticmethod
    def build_user_prompt(sections: Dict[str, str], max_total_length: int = MAX_PROMPT_LENGTH) -> str:
        """
        Build user prompt from sectionized note, trimming if needed to stay under limit.
        
        Args:
            sections: Dictionary with sectionized note data
            max_total_length: Maximum total prompt length (system + user)
                    
        Returns:
            Formatted user prompt string
        """
        # Get system prompt length
        system_prompt = PromptBuilder.get_system_prompt()
        system_length = len(system_prompt)
        
        # Calculate available length for user prompt
        # Reserve space for template structure (~500 chars) and some buffer
        template_overhead = 500
        available_length = max_total_length - system_length - template_overhead
        
        # Get values with fallback to empty string (not "not specified" to avoid confusion)
        history_present_illness = sections.get("History of Present Illness", "")
        chief_complaint = sections.get("Chief Complaint", "")
        past_medical_history = sections.get("Past Medical History", "")
        diagnoses = sections.get("Discharge Diagnosis", sections.get("Diagnoses", ""))
        hospital_course = sections.get("Hospital Course", "")
        discharge_medications = sections.get("Discharge Medications", "")
        discharge_instructions = sections.get("Discharge Instructions", "")
        followup = sections.get("Follow-up", "")
        allergies = sections.get("Allergies", "")
        pending_tests = sections.get("Pending Tests", "")
        diet_activity = sections.get("Diet/Activity", "")
        physical_exam = sections.get("Physical Exam", "")
        pertinent_results = sections.get("Pertinent Results", "")
        
        # Calculate current total length
        test_prompt = PromptBuilder.USER_TEMPLATE.format(
            history_present_illness=history_present_illness,
            chief_complaint=chief_complaint,
            past_medical_history=past_medical_history,
            diagnoses=diagnoses,
            hospital_course=hospital_course,
            discharge_medications=discharge_medications,
            discharge_instructions=discharge_instructions,
            followup=followup,
            allergies=allergies,
            pending_tests=pending_tests,
            diet_activity=diet_activity,
            physical_exam=physical_exam,
            pertinent_results=pertinent_results
        )
        
        total_length = system_length + len(test_prompt)
        
        # If over limit, trim sections proportionally
        if total_length > max_total_length:
            # Calculate how much to trim
            excess = total_length - max_total_length
            # Priority: keep diagnoses, medications, hospital course
            # Trim less important sections more
            section_lengths = {
                'diagnoses': len(diagnoses),
                'hospital_course': len(hospital_course),
                'discharge_medications': len(discharge_medications),
                'followup': len(followup),
                'allergies': len(allergies),
                'pending_tests': len(pending_tests),
                'diet_activity': len(diet_activity)
            }
            
            # Trim in order of priority (lower priority = trim more)
            # Priority: diagnoses > medications > hospital_course > others
            trim_order = ['pending_tests', 'diet_activity', 'followup', 'allergies', 
                          'hospital_course', 'discharge_medications', 'diagnoses']
            
            remaining_excess = excess
            for section_key in trim_order:
                if remaining_excess <= 0:
                    break
                    
                if section_key == 'diagnoses':
                    max_trim = min(remaining_excess * 0.1, len(diagnoses) * 0.3)
                    diagnoses = PromptBuilder._trim_text(diagnoses, len(diagnoses) - int(max_trim))
                elif section_key == 'hospital_course':
                    max_trim = min(remaining_excess * 0.2, len(hospital_course) * 0.4)
                    hospital_course = PromptBuilder._trim_text(hospital_course, len(hospital_course) - int(max_trim))
                elif section_key == 'discharge_medications':
                    max_trim = min(remaining_excess * 0.2, len(discharge_medications) * 0.3)
                    discharge_medications = PromptBuilder._trim_text(discharge_medications, len(discharge_medications) - int(max_trim))
                elif section_key == 'followup':
                    max_trim = min(remaining_excess * 0.3, len(followup) * 0.5)
                    followup = PromptBuilder._trim_text(followup, len(followup) - int(max_trim))
                elif section_key == 'allergies':
                    max_trim = min(remaining_excess * 0.1, len(allergies) * 0.5)
                    allergies = PromptBuilder._trim_text(allergies, len(allergies) - int(max_trim))
                elif section_key == 'pending_tests':
                    max_trim = min(remaining_excess * 0.3, len(pending_tests) * 0.5)
                    pending_tests = PromptBuilder._trim_text(pending_tests, len(pending_tests) - int(max_trim))
                elif section_key == 'diet_activity':
                    max_trim = min(remaining_excess * 0.3, len(diet_activity) * 0.5)
                    diet_activity = PromptBuilder._trim_text(diet_activity, len(diet_activity) - int(max_trim))
                
                # Recalculate
                test_prompt = PromptBuilder.USER_TEMPLATE.format(
                    history_present_illness=history_present_illness,
                    chief_complaint=chief_complaint,
                    past_medical_history=past_medical_history,
                    diagnoses=diagnoses,
                    hospital_course=hospital_course,
                    discharge_medications=discharge_medications,
                    discharge_instructions=discharge_instructions,
                    followup=followup,
                    allergies=allergies,
                    pending_tests=pending_tests,
                    diet_activity=diet_activity,
                    physical_exam=physical_exam,
                    pertinent_results=pertinent_results
                )
                total_length = system_length + len(test_prompt)
                remaining_excess = total_length - max_total_length
        
        return PromptBuilder.USER_TEMPLATE.format(
            history_present_illness=history_present_illness,
            chief_complaint=chief_complaint,
            past_medical_history=past_medical_history,
            diagnoses=diagnoses,
            hospital_course=hospital_course,
            discharge_medications=discharge_medications,
            discharge_instructions=discharge_instructions,
            followup=followup,
            allergies=allergies,
            pending_tests=pending_tests,
            diet_activity=diet_activity,
            physical_exam=physical_exam,
            pertinent_results=pertinent_results
        )
    
    @staticmethod
    def get_system_prompt() -> str:
        """Get the system prompt."""
        return PromptBuilder.SYSTEM_PROMPT
    
    @staticmethod
    def build_full_prompt(sections: Dict[str, str], max_total_length: int = MAX_PROMPT_LENGTH) -> Dict[str, str]:
        """
        Build complete prompt (system + user) for LLM, ensuring total length is under limit.
        
        Args:
            sections: Sectionized note dictionary
            max_total_length: Maximum total prompt length (default: 7000 for free tier)
            
        Returns:
            Dictionary with 'system' and 'user' prompts, and 'total_length'
        """
        system_prompt = PromptBuilder.get_system_prompt()
        user_prompt = PromptBuilder.build_user_prompt(sections, max_total_length)
        
        total_length = len(system_prompt) + len(user_prompt)
        
        return {
            "system": system_prompt,
            "user": user_prompt,
            "total_length": total_length
        }

