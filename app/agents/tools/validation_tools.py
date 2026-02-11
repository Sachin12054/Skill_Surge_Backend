"""
Validation and analysis tools for hypothesis agents
"""

from typing import Dict, Any, List
from langchain.tools import tool
import logging
import json

logger = logging.getLogger(__name__)


@tool
def execute_python_code(code: str) -> Dict[str, Any]:
    """
    Execute Python code for statistical validation or data analysis.
    Use this for calculating statistics, running simulations, or validating mathematical claims.
    
    Args:
        code: Python code to execute (must be safe and self-contained)
    
    Returns:
        Dictionary with execution result, output, or error
    """
    try:
        import sys
        from io import StringIO
        import math
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        # Create safe execution environment
        safe_globals = {
            'math': math,
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'float': float,
                'int': int,
                'str': str,
                'list': list,
                'dict': dict,
                'True': True,
                'False': False,
                'None': None,
            }
        }
        
        local_vars = {}
        
        # Execute code
        exec(code, safe_globals, local_vars)
        
        # Get output
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        # Get result (last assigned variable or None)
        result = local_vars.get('result', None)
        
        return {
            "success": True,
            "output": output.strip() if output else None,
            "result": str(result) if result is not None else None,
            "variables": {k: str(v) for k, v in local_vars.items() if not k.startswith('_')}
        }
        
    except Exception as e:
        logger.error(f"Code execution error: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@tool
def validate_statistical_claim(claim: str, data_description: str = "") -> Dict[str, Any]:
    """
    Validate statistical claims or research assertions using basic statistical reasoning.
    
    Args:
        claim: The statistical claim to validate
        data_description: Optional description of data or methodology
    
    Returns:
        Dictionary with validation result and reasoning
    """
    try:
        # Simple heuristic validation based on keywords
        confidence = 0.5
        warnings = []
        
        # Check for common statistical issues
        if "correlation" in claim.lower() and "causation" in claim.lower():
            warnings.append("⚠️ Correlation does not imply causation")
            confidence -= 0.2
        
        if "significant" in claim.lower() and not any(p in claim.lower() for p in ["p<", "p =", "p-value"]):
            warnings.append("⚠️ Significance claim without p-value")
            confidence -= 0.1
        
        if any(term in claim.lower() for term in ["proves", "confirms", "definitely"]):
            warnings.append("⚠️ Overly strong language - science rarely 'proves' things")
            confidence -= 0.15
        
        if "sample size" in data_description.lower():
            confidence += 0.2
            
        if any(term in data_description.lower() for term in ["randomized", "controlled", "blind"]):
            confidence += 0.2
        
        confidence = max(0.1, min(1.0, confidence))
        
        return {
            "valid": confidence > 0.5,
            "confidence": confidence,
            "warnings": warnings,
            "recommendations": [
                "Include confidence intervals" if "interval" not in claim.lower() else None,
                "Specify sample size" if "sample" not in data_description.lower() else None,
                "Describe methodology" if not data_description else None,
            ],
            "assessment": "Valid claim with minor concerns" if confidence > 0.6 else
                         "Questionable claim - needs clarification" if confidence > 0.3 else
                         "Invalid or unsupported claim"
        }
        
    except Exception as e:
        logger.error(f"Statistical validation error: {e}")
        return {"error": str(e)}


@tool
def score_hypothesis_testability(hypothesis: str, methodology: List[str] = None) -> Dict[str, Any]:
    """
    Score how testable/falsifiable a hypothesis is using scientific criteria.
    
    Args:
        hypothesis: The hypothesis statement
        methodology: List of suggested methodologies (optional)
    
    Returns:
        Dictionary with testability score and analysis
    """
    try:
        score = 0.5
        feedback = []
        
        # Check for measurable variables
        measurable_terms = ["measure", "quantify", "count", "rate", "level", "amount", "frequency", "correlation"]
        if any(term in hypothesis.lower() for term in measurable_terms):
            score += 0.2
            feedback.append("✓ Contains measurable variables")
        else:
            feedback.append("✗ Lacks clearly measurable variables")
        
        # Check for specific predictions
        prediction_terms = ["increase", "decrease", "higher", "lower", "more", "less", "affect", "influence"]
        if any(term in hypothesis.lower() for term in prediction_terms):
            score += 0.15
            feedback.append("✓ Makes specific predictions")
        else:
            feedback.append("✗ Predictions are vague")
        
        # Check for falsifiability
        if any(term in hypothesis.lower() for term in ["always", "never", "all", "none", "every"]):
            score -= 0.1
            feedback.append("⚠️ Overly absolute - may not be falsifiable")
        else:
            score += 0.1
            feedback.append("✓ Allows for falsification")
        
        # Methodology bonus
        if methodology and len(methodology) > 0:
            score += 0.15
            feedback.append(f"✓ {len(methodology)} methodologies suggested")
        
        score = max(0.0, min(1.0, score))
        
        return {
            "testability_score": score,
            "feedback": feedback,
            "is_testable": score > 0.6,
            "suggested_improvements": [
                "Add measurable outcome variables" if score < 0.5 else None,
                "Specify testable predictions" if "prediction" not in " ".join(feedback).lower() else None,
                "Define clear experimental conditions" if not methodology else None,
            ],
            "assessment": "Highly testable hypothesis" if score > 0.75 else
                         "Moderately testable" if score > 0.5 else
                         "Difficult to test - needs refinement"
        }
        
    except Exception as e:
        logger.error(f"Testability scoring error: {e}")
        return {"error": str(e)}


@tool
def analyze_research_feasibility(
    hypothesis: str,
    required_resources: List[str] = None,
    timeframe: str = ""
) -> Dict[str, Any]:
    """
    Analyze the practical feasibility of conducting research on a hypothesis.
    
    Args:
        hypothesis: The hypothesis to analyze
        required_resources: List of required resources (equipment, data, etc.)
        timeframe: Expected research timeframe
    
    Returns:
        Dictionary with feasibility assessment
    """
    try:
        feasibility = 0.7
        challenges = []
        
        # Check for complexity indicators
        if any(term in hypothesis.lower() for term in ["neural", "brain", "quantum", "molecular"]):
            feasibility -= 0.2
            challenges.append("Requires specialized equipment or expertise")
        
        if any(term in hypothesis.lower() for term in ["longitudinal", "long-term", "decades"]):
            feasibility -= 0.15
            challenges.append("Long-term study may be challenging")
        
        # Resource considerations
        if required_resources:
            if len(required_resources) > 5:
                feasibility -= 0.1
                challenges.append("Multiple resources required")
            elif len(required_resources) <= 2:
                feasibility += 0.1
        
        # Ethical considerations
        if any(term in hypothesis.lower() for term in ["human", "patient", "participant", "clinical"]):
            challenges.append("Requires IRB approval and ethical oversight")
            feasibility -= 0.05
        
        feasibility = max(0.1, min(1.0, feasibility))
        
        return {
            "feasibility_score": feasibility,
            "challenges": challenges if challenges else ["No major challenges identified"],
            "is_feasible": feasibility > 0.5,
            "recommendations": [
                "Consider computational modeling as alternative" if feasibility < 0.4 else None,
                "Start with pilot study" if feasibility < 0.6 else None,
                "Collaborate with specialized labs" if "specialized" in str(challenges) else None,
            ],
            "estimated_difficulty": "Low difficulty" if feasibility > 0.75 else
                                   "Moderate difficulty" if feasibility > 0.5 else
                                   "High difficulty - may need significant resources"
        }
        
    except Exception as e:
        logger.error(f"Feasibility analysis error: {e}")
        return {"error": str(e)}
