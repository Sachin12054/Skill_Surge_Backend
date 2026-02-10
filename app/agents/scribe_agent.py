from typing import Dict, Any, Optional
from app.core import get_bedrock_service
import json
import re


class ScribeAgent:
    """Agent for converting images of notes to code/math."""
    
    def __init__(self):
        self.bedrock = get_bedrock_service()
    
    async def analyze_image(
        self,
        image_base64: str,
        output_type: str,
        media_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Analyze an image and convert to the requested output type.
        
        Args:
            image_base64: Base64 encoded image
            output_type: 'math', 'code', or 'diagram'
            media_type: MIME type of the image
        
        Returns:
            Dictionary with result, format, and confidence
        """
        prompts = {
            "math": self._get_math_prompt(),
            "code": self._get_code_prompt(),
            "diagram": self._get_diagram_prompt(),
        }
        
        prompt = prompts.get(output_type, prompts["math"])
        
        response = await self.bedrock.invoke_claude_vision(
            prompt=prompt,
            image_base64=image_base64,
            image_media_type=media_type,
            system_prompt="You are an expert at converting handwritten content to digital formats.",
        )
        
        # Parse the response
        result = self._parse_response(response, output_type)
        
        return result
    
    def _get_math_prompt(self) -> str:
        return """Analyze this handwritten mathematical content and convert it to LaTeX.

Instructions:
1. Identify all mathematical expressions, equations, and formulas
2. Convert them to proper LaTeX syntax
3. Preserve the structure and layout
4. Include any text labels or annotations
5. If there are multiple equations, use align or gather environments

Return a JSON object with:
- latex: The LaTeX code
- description: Brief description of what the math represents
- confidence: Your confidence in the transcription (0-1)
- suggestions: Array of any improvements or clarifications needed

Return ONLY the JSON object."""

    def _get_code_prompt(self) -> str:
        return """Analyze this handwritten code or pseudocode and convert it to working code.

Instructions:
1. Identify the programming language (or infer the best one)
2. Convert handwritten code to properly formatted code
3. Fix any obvious syntax errors
4. Add appropriate comments
5. Ensure proper indentation

Return a JSON object with:
- code: The converted code
- language: Detected/chosen programming language
- description: Brief description of what the code does
- confidence: Your confidence in the transcription (0-1)
- suggestions: Array of improvements or potential issues

Return ONLY the JSON object."""

    def _get_diagram_prompt(self) -> str:
        return """Analyze this handwritten diagram and convert it to a Mermaid diagram.

Instructions:
1. Identify the type of diagram (flowchart, sequence, class, etc.)
2. Extract all nodes/entities and their relationships
3. Convert to proper Mermaid syntax
4. Preserve the logical structure

Return a JSON object with:
- mermaid: The Mermaid diagram code
- diagram_type: Type of diagram detected
- description: Brief description of what the diagram represents
- confidence: Your confidence in the transcription (0-1)
- suggestions: Array of any clarifications needed

Return ONLY the JSON object."""

    def _parse_response(self, response: str, output_type: str) -> Dict[str, Any]:
        """Parse the AI response into structured output."""
        try:
            # Clean up the response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            
            # Map to expected format
            format_map = {
                "math": "latex",
                "code": data.get("language", "python"),
                "diagram": "mermaid",
            }
            
            result_key = {
                "math": "latex",
                "code": "code",
                "diagram": "mermaid",
            }
            
            return {
                "result": data.get(result_key[output_type], ""),
                "format": format_map[output_type],
                "confidence": data.get("confidence", 0.8),
                "description": data.get("description", ""),
                "suggestions": data.get("suggestions", []),
            }
        except json.JSONDecodeError:
            # Fallback: try to extract content directly
            return {
                "result": response,
                "format": "text",
                "confidence": 0.5,
                "description": "Raw AI output (parsing failed)",
                "suggestions": ["Manual review recommended"],
            }
    
    async def validate_math(self, latex: str) -> Dict[str, Any]:
        """Validate LaTeX syntax and mathematical correctness."""
        prompt = f"""Validate this LaTeX mathematical expression:

{latex}

Check for:
1. Syntax correctness
2. Mathematical validity
3. Common errors or typos
4. Potential improvements

Return a JSON object with:
- is_valid: boolean
- syntax_issues: array of syntax problems
- math_issues: array of mathematical issues
- corrected_latex: corrected version if needed
- confidence: confidence in the validation

Return ONLY the JSON object."""

        response = await self.bedrock.invoke_claude(prompt)
        
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except json.JSONDecodeError:
            return {"is_valid": True, "confidence": 0.5}


def get_scribe_agent() -> ScribeAgent:
    """Get scribe agent instance."""
    return ScribeAgent()
