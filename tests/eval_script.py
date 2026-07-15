import sys
from pathlib import Path

# Add project root to path so we can import backend packages
sys.path.append(str(Path(__file__).resolve().parent.parent))

from unittest.mock import MagicMock
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['faiss'] = MagicMock()

import backend.app.rag
backend.app.rag.HAS_SEMANTIC_LIBS = False

from backend.app.database import init_db
from backend.app.llm import query_stadium_assistant

def run_evaluation():
    print("==================================================")
    print("       EktaAI LLM ORCHESTRATION EVALUATION        ")
    print("==================================================")
    
    # Initialize database for testing environment
    init_db()
    
    test_cases = [
        {
            "id": 1,
            "prompt": "Where is the main medical center?",
            "is_staff": False,
            "expected_tool": None,
            "desc": "Check RAG for medical location info",
            "lang": "en"
        },
        {
            "id": 2,
            "prompt": "How do I get to Gate 3?",
            "is_staff": False,
            "expected_tool": "get_route",
            "desc": "General route planning trigger",
            "lang": "en"
        },
        {
            "id": 3,
            "prompt": "Can I borrow a wheelchair at the stadium?",
            "is_staff": False,
            "expected_tool": None,
            "desc": "Check RAG for wheelchair borrowing details",
            "lang": "en"
        },
        {
            "id": 4,
            "prompt": "¿Dónde están los baños accesibles?",
            "is_staff": False,
            "expected_tool": None,
            "desc": "Spanish query about accessible restrooms",
            "lang": "es"
        },
        {
            "id": 5,
            "prompt": "What is the crowd density at Zone-C?",
            "is_staff": False,
            "expected_tool": "get_crowd_density",
            "desc": "Zone crowd status query",
            "lang": "en"
        },
        {
            "id": 6,
            "prompt": "Is Gate 2 open or closed right now?",
            "is_staff": False,
            "expected_tool": "get_gate_status",
            "desc": "Gate congestion & status tool check",
            "lang": "en"
        },
        {
            "id": 7,
            "prompt": "How do I get from Gate 2 to Section 204 with a wheelchair?",
            "is_staff": False,
            "expected_tool": "get_route",
            "desc": "Route query needing accessible elevator path",
            "lang": "en"
        },
        {
            "id": 8,
            "prompt": "What items are prohibited inside the stadium?",
            "is_staff": False,
            "expected_tool": None,
            "desc": "Check RAG policy rules context",
            "lang": "en"
        },
        {
            "id": 9,
            "prompt": "¿Hay comida Halal o vegetariana?",
            "is_staff": False,
            "expected_tool": None,
            "desc": "Spanish query about dining options",
            "lang": "es"
        },
        {
            "id": 10,
            "prompt": "Tell me about Metro Line A transit connections.",
            "is_staff": False,
            "expected_tool": None,
            "desc": "Check RAG transit rules",
            "lang": "en"
        },
        {
            "id": 11,
            "prompt": "Where is the Lost and Found office?",
            "is_staff": False,
            "expected_tool": None,
            "desc": "Check RAG lost & found guidelines",
            "lang": "en"
        },
        {
            "id": 12,
            "prompt": "What are the rules about bag size for match day?",
            "is_staff": False,
            "expected_tool": None,
            "desc": "Check bag restriction policies",
            "lang": "en"
        },
        {
            "id": 13,
            "prompt": "Route me from Gate 3 to Section 305",
            "is_staff": False,
            "expected_tool": "get_route",
            "desc": "General routing search",
            "lang": "en"
        },
        {
            "id": 14,
            "prompt": "What are the gate opening hours and entry restrictions?",
            "is_staff": False,
            "expected_tool": None,
            "desc": "Check hours policies",
            "lang": "en"
        },
        {
            "id": 15,
            "prompt": "¿Cómo llego de Gate 1 a Section 102 en silla de ruedas?",
            "is_staff": False,
            "expected_tool": "get_route",
            "desc": "Spanish route planning with accessibility check",
            "lang": "es"
        },
        {
            "id": 16,
            "prompt": "What is the crowd density at Zone-C?",
            "is_staff": True,
            "expected_tool": "get_crowd_density",
            "desc": "Staff query for crowd density at Zone-C",
            "lang": "en"
        },
        {
            "id": 17,
            "prompt": "Is Gate 2 open or closed right now?",
            "is_staff": True,
            "expected_tool": "get_gate_status",
            "desc": "Staff query for Gate 2 status",
            "lang": "en"
        }
    ]
    
    passed_count = 0
    
    print(f"{'ID':<3} | {'Prompt':<45} | {'Exp. Tool':<18} | {'Act. Tool':<18} | {'Lang':<4} | {'Status':<6}")
    print("-" * 105)
    
    from backend.app.llm_client import MockLLMClient
    print("\nLOG: Run is explicitly using MockLLMClient (Test double)")
 
    for case in test_cases:
        res = query_stadium_assistant(case["prompt"], is_staff=case["is_staff"], client=MockLLMClient())
        
        reply = res.get("reply", "")
        tool_called = res.get("tool_called")
        
        # Validation checks
        has_content = len(reply.strip()) > 0
        correct_tool = tool_called == case["expected_tool"]
        
        correct_lang = True
        if case["lang"] == "es":
            # Heuristics: check for Spanish stop words or content
            spanish_words = ["el", "la", "en", "para", "los", "las", "con", "he", "trazado", "centro", "baño", "puerta"]
            correct_lang = any(word in reply.lower() for word in spanish_words)
            
        is_staff_reply_sane = True
        if case["is_staff"]:
            # Ensure staff replies do not contain JSON format/empty alerts object
            is_staff_reply_sane = "{\"alerts\"" not in reply
            
        is_sane = has_content and correct_tool and correct_lang and is_staff_reply_sane
        
        status_str = "PASS" if is_sane else "FAIL"
        if is_sane:
            passed_count += 1
            
        # Truncate prompt for alignment
        prompt_trunc = case["prompt"][:42] + "..." if len(case["prompt"]) > 45 else case["prompt"]
        print(f"{case['id']:<3} | {prompt_trunc:<45} | {str(case['expected_tool']):<18} | {str(tool_called):<18} | {case['lang']:<4} | {status_str:<6}")
        
        if not is_sane:
            # Print error detail to diagnose
            print(f"    --> Error Detail: Content? {has_content}, Tool Match? {correct_tool} (exp: {case['expected_tool']}, got: {tool_called}), Lang Match? {correct_lang}, Staff Sane? {is_staff_reply_sane}")
            print(f"    --> Reply: {reply[:120]}...")
            
    print("-" * 105)
    print(f"Results: {passed_count} / {len(test_cases)} Passed ({int(passed_count/len(test_cases)*100)}%)")
    print("==================================================")
    
    if passed_count == len(test_cases):
        print("Success: All test scenarios passed sanitization, translation, and tool checks!")
        sys.exit(0)
    else:
        print("Warning: Some evaluation checks failed. Review outputs.")
        sys.exit(1)

if __name__ == "__main__":
    run_evaluation()
