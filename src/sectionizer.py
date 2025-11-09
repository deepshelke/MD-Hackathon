"""
Sectionizer for MIMIC-IV discharge and radiology notes.
Extracts structured sections from raw note text.
"""
import re
from typing import Dict, Optional


class DischargeNoteSectionizer:
    """Extracts sections from discharge notes."""
    
    # Section patterns - ordered by typical appearance in notes
    SECTION_PATTERNS = {
        "Allergies": [
            r'Allergies?[:\s]*\n',
            r'Allergies?\s*/\s*Adverse\s+Drug\s+Reactions[:\s]*\n',
        ],
        "Discharge Diagnosis": [
            r'Discharge\s+Diagnos(?:is|es)[:\s]*\n',
            r'Discharge\s+Diagnosis[:\s]*\n',
        ],
        "Hospital Course": [
            r'Hospital\s+Course[:\s]*\n',
        ],
        "Discharge Medications": [
            r'Discharge\s+Medications?[:\s]*\n',
            r'Discharge\s+Medication[:\s]*\n',
        ],
        "Follow-up": [
            r'Follow[-\s]?up[:\s]*\n',
            r'Followup[:\s]*\n',
            r'Follow[-\s]?Up[:\s]*\n',
        ],
        "Pending Tests": [
            r'Pending\s+Tests?[:\s]*\n',
            r'Pending\s+Test[:\s]*\n',
        ],
        "Diet/Activity": [
            r'Diet[:\s]*\n',
            r'Activity[:\s]*\n',
            r'Discharge\s+Instructions?[:\s]*\n',
        ],
    }
    
    # Alternative section names that map to our standard names
    SECTION_MAPPING = {
        "Diagnoses": "Discharge Diagnosis",
        "Medications": "Discharge Medications",
        "Followup": "Follow-up",
        "Follow Up": "Follow-up",
        "Discharge Instructions": "Diet/Activity",  # Often contains diet/activity info
    }
    
    @staticmethod
    def extract_sections(note_text: str) -> Dict[str, str]:
        """
        Extract sections from a discharge note.
        
        Args:
            note_text: Raw discharge note text
            
        Returns:
            Dictionary with section names as keys and section text as values.
            Keys: "Diagnoses", "Hospital Course", "Discharge Medications", 
                  "Follow-up", "Allergies", "Pending Tests", "Diet/Activity"
        """
        sections = {
            "Diagnoses": "",
            "Hospital Course": "",
            "Discharge Medications": "",
            "Follow-up": "",
            "Allergies": "",
            "Pending Tests": "",
            "Diet/Activity": ""
        }
        
        # Find all section boundaries
        section_boundaries = []
        
        # Find matches for each section type
        for section_name, patterns in DischargeNoteSectionizer.SECTION_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, note_text, re.IGNORECASE | re.MULTILINE):
                    # Map to standard section name
                    standard_name = DischargeNoteSectionizer._map_section_name(section_name)
                    section_boundaries.append((match.end(), standard_name))
        
        # Sort by position
        section_boundaries.sort(key=lambda x: x[0])
        
        # Extract text for each section
        for i, (start_pos, section_name) in enumerate(section_boundaries):
            # Find end position (next section or end of text)
            end_pos = section_boundaries[i + 1][0] if i + 1 < len(section_boundaries) else len(note_text)
            
            # Extract section text
            section_text = note_text[start_pos:end_pos].strip()
            
            # Stop at next major section header (if not already at boundary)
            # Look for common section headers that might appear within text
            next_section_match = re.search(
                r'\n(?:Discharge\s+(?:Diagnos|Medication|Instruction)|Hospital\s+Course|Follow[-\s]?up|Allergies?|Pending\s+Test|Diet|Activity)[:\s]*\n',
                section_text,
                re.IGNORECASE
            )
            if next_section_match:
                section_text = section_text[:next_section_match.start()].strip()
            
            # Handle multiple occurrences of same section (append)
            if sections[section_name]:
                sections[section_name] += "\n\n" + section_text
            else:
                sections[section_name] = section_text
        
        # If no sections found, try alternative extraction methods
        if not any(sections.values()):
            sections = DischargeNoteSectionizer._extract_sections_fallback(note_text)
        
        return sections
    
    @staticmethod
    def _map_section_name(section_name: str) -> str:
        """Map section name to standard name."""
        # Direct match
        standard_names = {
            "Allergies": "Allergies",
            "Discharge Diagnosis": "Diagnoses",
            "Hospital Course": "Hospital Course",
            "Discharge Medications": "Discharge Medications",
            "Follow-up": "Follow-up",
            "Pending Tests": "Pending Tests",
            "Diet/Activity": "Diet/Activity",
        }
        
        if section_name in standard_names:
            return standard_names[section_name]
        
        # Check mapping
        if section_name in DischargeNoteSectionizer.SECTION_MAPPING:
            mapped = DischargeNoteSectionizer.SECTION_MAPPING[section_name]
            return standard_names.get(mapped, section_name)
        
        return section_name
    
    @staticmethod
    def _extract_sections_fallback(note_text: str) -> Dict[str, str]:
        """
        Fallback method to extract sections when standard patterns don't match.
        Uses keyword-based extraction.
        """
        sections = {
            "Diagnoses": "",
            "Hospital Course": "",
            "Discharge Medications": "",
            "Follow-up": "",
            "Allergies": "",
            "Pending Tests": "",
            "Diet/Activity": ""
        }
        
        # Try to find allergies early in the note
        allergies_match = re.search(r'Allergies?[:\s]*\n(.*?)(?=\n\n|\n[A-Z][a-z]+[:\s]*\n|$)', 
                                    note_text, re.IGNORECASE | re.DOTALL)
        if allergies_match:
            sections["Allergies"] = allergies_match.group(1).strip()
        
        # Try to find discharge diagnosis
        diagnosis_match = re.search(r'Discharge\s+Diagnos(?:is|es)[:\s]*\n(.*?)(?=\n\n|\n[A-Z][a-z]+[:\s]*\n|$)', 
                                     note_text, re.IGNORECASE | re.DOTALL)
        if diagnosis_match:
            sections["Diagnoses"] = diagnosis_match.group(1).strip()
        
        # Try to find hospital course
        course_match = re.search(r'Hospital\s+Course[:\s]*\n(.*?)(?=\n\n|\nDischarge|$)', 
                                 note_text, re.IGNORECASE | re.DOTALL)
        if course_match:
            sections["Hospital Course"] = course_match.group(1).strip()
        
        # Try to find discharge medications
        meds_match = re.search(r'Discharge\s+Medications?[:\s]*\n(.*?)(?=\n\n|\n[A-Z][a-z]+[:\s]*\n|$)', 
                               note_text, re.IGNORECASE | re.DOTALL)
        if meds_match:
            sections["Discharge Medications"] = meds_match.group(1).strip()
        
        # Try to find follow-up
        followup_match = re.search(r'Follow[-\s]?up[:\s]*\n(.*?)(?=\n\n|\n[A-Z][a-z]+[:\s]*\n|$)', 
                                   note_text, re.IGNORECASE | re.DOTALL)
        if followup_match:
            sections["Follow-up"] = followup_match.group(1).strip()
        
        return sections
    
    @staticmethod
    def clean_section_text(text: str) -> str:
        """Clean extracted section text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text


class RadiologyNoteSectionizer:
    """Extracts sections from radiology notes."""
    
    # Section patterns - ordered by typical appearance in radiology notes
    # Note: Sections can have content on same line or next line after header
    SECTION_PATTERNS = {
        "Examination": [
            r'EXAMINATION[:\s]+',
            r'EXAM[:\s]+',
        ],
        "Indication": [
            r'INDICATION[:\s]+',
            r'CLINICAL\s+INDICATION[:\s]+',
            r'HISTORY[:\s]+',
        ],
        "Technique": [
            r'TECHNIQUE[:\s]+',
            r'METHOD[:\s]+',
        ],
        "Comparison": [
            r'COMPARISON[:\s]+',
            r'PRIOR\s+STUDIES?[:\s]+',
        ],
        "Findings": [
            r'FINDINGS?[:\s]+',
            r'DESCRIPTION[:\s]+',
        ],
        "Procedure": [
            r'PROCEDURE[:\s]+',
            r'PROCEDURAL\s+DETAILS?[:\s]+',
        ],
        "Impression": [
            r'IMPRESSION[:\s]+',
            r'CONCLUSION[:\s]+',
            r'INTERPRETATION[:\s]+',
        ],
    }
    
    @staticmethod
    def extract_sections(note_text: str) -> Dict[str, str]:
        """
        Extract sections from a radiology note.
        
        Args:
            note_text: Raw radiology note text
            
        Returns:
            Dictionary with section names as keys and section text as values.
            Keys: "Examination", "Indication", "Technique", "Comparison", 
                  "Findings", "Procedure", "Impression"
        """
        sections = {
            "Examination": "",
            "Indication": "",
            "Technique": "",
            "Comparison": "",
            "Findings": "",
            "Procedure": "",
            "Impression": ""
        }
        
        # Find all section boundaries
        section_boundaries = []
        
        # Find matches for each section type
        for section_name, patterns in RadiologyNoteSectionizer.SECTION_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, note_text, re.IGNORECASE | re.MULTILINE):
                    # Start position is after the header
                    # Content can be on same line or next line
                    header_end = match.end()
                    section_boundaries.append((header_end, section_name))
        
        # Sort by position
        section_boundaries.sort(key=lambda x: x[0])
        
        # Extract text for each section
        for i, (start_pos, section_name) in enumerate(section_boundaries):
            # Find end position (next section or end of text)
            end_pos = section_boundaries[i + 1][0] if i + 1 < len(section_boundaries) else len(note_text)
            
            # Extract section text (from after header to next section)
            section_text = note_text[start_pos:end_pos].strip()
            
            # Remove any trailing section headers that might have been captured
            # Look for common radiology section headers at the end
            next_section_match = re.search(
                r'\n(?:EXAMINATION|INDICATION|TECHNIQUE|COMPARISON|FINDINGS?|PROCEDURE|IMPRESSION|CONCLUSION)[:\s]+',
                section_text,
                re.IGNORECASE
            )
            if next_section_match:
                section_text = section_text[:next_section_match.start()].strip()
            
            # Clean up: remove content from next section header if present
            # This handles cases where header content is on same line
            lines = section_text.split('\n')
            cleaned_lines = []
            for line in lines:
                # Stop if we hit a new section header
                if re.match(r'^(?:EXAMINATION|INDICATION|TECHNIQUE|COMPARISON|FINDINGS?|PROCEDURE|IMPRESSION|CONCLUSION)[:\s]+', line, re.IGNORECASE):
                    break
                cleaned_lines.append(line)
            section_text = '\n'.join(cleaned_lines).strip()
            
            # Handle multiple occurrences of same section (append)
            if sections[section_name]:
                sections[section_name] += "\n\n" + section_text
            else:
                sections[section_name] = section_text
        
        # If no sections found, try alternative extraction methods
        if not any(sections.values()):
            sections = RadiologyNoteSectionizer._extract_sections_fallback(note_text)
        
        return sections
    
    @staticmethod
    def _extract_sections_fallback(note_text: str) -> Dict[str, str]:
        """
        Fallback method to extract sections when standard patterns don't match.
        Uses keyword-based extraction.
        """
        sections = {
            "Examination": "",
            "Indication": "",
            "Technique": "",
            "Comparison": "",
            "Findings": "",
            "Procedure": "",
            "Impression": ""
        }
        
        # Try to find examination
        exam_match = re.search(r'EXAMINATION[:\s]*\n(.*?)(?=\n\n|\n(?:INDICATION|TECHNIQUE|FINDINGS|IMPRESSION)[:\s]*\n|$)', 
                               note_text, re.IGNORECASE | re.DOTALL)
        if exam_match:
            sections["Examination"] = exam_match.group(1).strip()
        
        # Try to find indication
        indication_match = re.search(r'INDICATION[:\s]*\n(.*?)(?=\n\n|\n(?:TECHNIQUE|FINDINGS|IMPRESSION)[:\s]*\n|$)', 
                                     note_text, re.IGNORECASE | re.DOTALL)
        if indication_match:
            sections["Indication"] = indication_match.group(1).strip()
        
        # Try to find technique
        technique_match = re.search(r'TECHNIQUE[:\s]*\n(.*?)(?=\n\n|\n(?:COMPARISON|FINDINGS|IMPRESSION)[:\s]*\n|$)', 
                                    note_text, re.IGNORECASE | re.DOTALL)
        if technique_match:
            sections["Technique"] = technique_match.group(1).strip()
        
        # Try to find comparison
        comparison_match = re.search(r'COMPARISON[:\s]*\n(.*?)(?=\n\n|\n(?:FINDINGS|IMPRESSION)[:\s]*\n|$)', 
                                     note_text, re.IGNORECASE | re.DOTALL)
        if comparison_match:
            sections["Comparison"] = comparison_match.group(1).strip()
        
        # Try to find findings
        findings_match = re.search(r'FINDINGS?[:\s]*\n(.*?)(?=\n\n|\n(?:PROCEDURE|IMPRESSION|CONCLUSION)[:\s]*\n|$)', 
                                   note_text, re.IGNORECASE | re.DOTALL)
        if findings_match:
            sections["Findings"] = findings_match.group(1).strip()
        
        # Try to find procedure
        procedure_match = re.search(r'PROCEDURE[:\s]*\n(.*?)(?=\n\n|\n(?:IMPRESSION|CONCLUSION)[:\s]*\n|$)', 
                                   note_text, re.IGNORECASE | re.DOTALL)
        if procedure_match:
            sections["Procedure"] = procedure_match.group(1).strip()
        
        # Try to find impression
        impression_match = re.search(r'IMPRESSION[:\s]*\n(.*?)(?=\n\n|$)', 
                                    note_text, re.IGNORECASE | re.DOTALL)
        if impression_match:
            sections["Impression"] = impression_match.group(1).strip()
        
        return sections
    
    @staticmethod
    def clean_section_text(text: str) -> str:
        """Clean extracted section text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text

