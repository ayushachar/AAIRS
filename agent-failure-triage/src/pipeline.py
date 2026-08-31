import os
import re
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from src.schemas import FailureLayer, TriageDiagnosis
from src.verifier import normalize_text, verify_evidence

SYSTEM_PROMPT = """You are an elite AI Systems & Site Reliability Engineer designed for the Agent Failure Triage Platform.
Your mission is to perform strict Failure Mode and Effects Analysis (FMEA) on raw AI telemetry traces.

INSTRUCTIONS:
1. Classify the root cause into exactly ONE of the 8 taxonomic FailureLayers.
2. Provide a concise, action-oriented root_cause_summary.
3. Suggest a deterministic suggested_remediation.
4. ZERO-TOKEN GROUNDING: You MUST extract exact substrings directly from the raw trace for cited_evidence. Paraphrasing or synthesizing log lines is STRICTLY FORBIDDEN and will cause pipeline rejection.
"""

LAYER_SIGNALS: List[tuple[FailureLayer, List[str]]] = [
    (
        FailureLayer.L1_TOOL_AND_SCHEMA_CONTRACTS,
        [
            "schema mismatch",
            "tool contract",
            "type coercion",
            "missing key",
            "enum drift",
            "stringified json",
        ],
    ),
    (
        FailureLayer.L2_RETRIEVAL_AND_RAG,
        [
            "semantic drift",
            "chunk boundary",
            "rag failure",
            "rag",
            "stale index",
            "empty context",
            "poison doc",
            "evidence not found due to rag",
        ],
    ),
    (
        FailureLayer.L3_INFRASTRUCTURE_AND_EXTERNAL_APIS,
        [
            "http 429",
            "503",
            "bearer token",
            "timeout",
            "pool exhaustion",
            "rate-limit",
            "gateway timeout",
            "infrastructure connection timeout",
        ],
    ),
    (
        FailureLayer.L4_CONTEXT_WINDOW_AND_TOKEN_LIMITS,
        [
            "token overflow",
            "context length exceeded",
            "json truncation",
            "lost in the middle",
        ],
    ),
    (
        FailureLayer.L5_ORCHESTRATION_AND_ROUTING,
        [
            "routing loop",
            "orchestration",
            "intent misclass",
            "missing fallback",
            "handoff",
            "routed to agent",
        ],
    ),
    (
        FailureLayer.L6_RETRY_LOGIC_AND_SIDE_EFFECTS,
        [
            "non-idempotent",
            "retry storm",
            "double mutation",
            "silent exception",
            "retrying idempotent mutation",
        ],
    ),
    (
        FailureLayer.L7_MODEL_BEHAVIOR_AND_PROMPT_DRIFT,
        [
            "safety refusal",
            "delimiter breakage",
            "prompt injection",
            "prompt drift",
            "model behavior",
        ],
    ),
    (
        FailureLayer.L8_STATE_CACHE_AND_CONCURRENCY,
        [
            "race condition",
            "dirty cache",
            "concurrency",
            "stale cache",
            "session hydration",
            "shared session memory",
        ],
    ),
]

REMEDIATIONS: Dict[FailureLayer, str] = {
    FailureLayer.L1_TOOL_AND_SCHEMA_CONTRACTS: (
        "Validate tool schemas at compile time; enforce strict JSON parsing and enum contracts."
    ),
    FailureLayer.L2_RETRIEVAL_AND_RAG: (
        "Refresh vector index; tune chunk boundaries and empty-context thresholds."
    ),
    FailureLayer.L3_INFRASTRUCTURE_AND_EXTERNAL_APIS: (
        "Add exponential backoff for 429/503; rotate bearer tokens; increase timeout budgets."
    ),
    FailureLayer.L4_CONTEXT_WINDOW_AND_TOKEN_LIMITS: (
        "Apply edge-preserving trace pruning; split long histories; use summarization."
    ),
    FailureLayer.L5_ORCHESTRATION_AND_ROUTING: (
        "Add routing fallbacks; cap multi-agent handoff depth; persist state across handoffs."
    ),
    FailureLayer.L6_RETRY_LOGIC_AND_SIDE_EFFECTS: (
        "Use idempotency keys; backoff retry storms; surface masked exceptions."
    ),
    FailureLayer.L7_MODEL_BEHAVIOR_AND_PROMPT_DRIFT: (
        "Harden delimiters; audit system prompts; validate tool-sourced content."
    ),
    FailureLayer.L8_STATE_CACHE_AND_CONCURRENCY: (
        "Add session locking; invalidate stale cache on writes; use optimistic concurrency."
    ),
}

SUMMARIES: Dict[FailureLayer, str] = {
    FailureLayer.L1_TOOL_AND_SCHEMA_CONTRACTS: "Tool or schema contract violation detected in telemetry.",
    FailureLayer.L2_RETRIEVAL_AND_RAG: "Retrieval or RAG pipeline failure caused context degradation.",
    FailureLayer.L3_INFRASTRUCTURE_AND_EXTERNAL_APIS: "External API or infrastructure failure blocked execution.",
    FailureLayer.L4_CONTEXT_WINDOW_AND_TOKEN_LIMITS: "Context window or token limit exceeded during generation.",
    FailureLayer.L5_ORCHESTRATION_AND_ROUTING: "Multi-agent orchestration or routing failure detected.",
    FailureLayer.L6_RETRY_LOGIC_AND_SIDE_EFFECTS: "Unsafe retry logic caused duplicate side effects.",
    FailureLayer.L7_MODEL_BEHAVIOR_AND_PROMPT_DRIFT: "Model behavior drift or prompt integrity issue detected.",
    FailureLayer.L8_STATE_CACHE_AND_CONCURRENCY: "State, cache, or concurrency conflict corrupted session data.",
}


class TriageState(TypedDict):
    raw_trace: str
    pruned_trace: str
    diagnosis: Optional[Dict[str, Any]]
    retries: int
    feedback: Optional[str]
    is_verified: bool
    unverified_snippets: List[str]
    reflection_logs: List[str]
    reflection_executed: bool


def _find_matching_lines(raw_trace: str, keywords: List[str], prefer: Optional[List[str]] = None) -> List[str]:
    lines = raw_trace.split("\n")
    matches: List[str] = []

    if prefer:
        for snippet in prefer:
            for line in lines:
                if snippet.strip() in line or line.strip() in snippet.strip():
                    if line not in matches:
                        matches.append(line)

    for line in lines:
        normalized = normalize_text(line)
        if any(keyword in normalized for keyword in keywords):
            if line not in matches:
                matches.append(line)

    return matches[:3]


def _extract_context(evidence_line: str, fallback_msg: str) -> str:
    path_match = re.search(r"(/[\w/.\-]+:\d+)", evidence_line)
    field_match = re.search(r"(KeyError|missing key|not found)[:]?\s*['\"]?([A-Za-z0-9_]+)['\"]?", evidence_line, re.IGNORECASE)
    
    details = []
    if path_match:
        details.append(f"at file location {path_match.group(1)}")
    if field_match:
        details.append(f"missing field '{field_match.group(2)}'")
        
    line_segment = evidence_line.strip()[:80] + "..." if len(evidence_line) > 80 else evidence_line.strip()
    if details:
        return f"{fallback_msg} (Extracted specifics: {', '.join(details)} from '{line_segment}')"
    return f"{fallback_msg} (Context: '{line_segment}')"


def _classify_trace(raw_trace: str, feedback: Optional[str] = None) -> TriageDiagnosis:
    prefer: Optional[List[str]] = None
    if feedback:
        bracket_match = re.search(r"\[(.*?)\]", feedback)
        if bracket_match:
            prefer = [s.strip().strip("'\"") for s in bracket_match.group(1).split(",")]

    pruned_normalized = normalize_text(raw_trace)

    for layer, keywords in LAYER_SIGNALS:
        if any(keyword in pruned_normalized for keyword in keywords):
            evidence = _find_matching_lines(raw_trace, keywords, prefer)
            if not evidence:
                for line in raw_trace.split("\n"):
                    if any(k in normalize_text(line) for k in keywords):
                        evidence.append(line)
                        break
            if not evidence:
                evidence = [raw_trace.split("\n")[0] if raw_trace else "ERROR: unknown failure"]

            return TriageDiagnosis(
                layer=layer,
                root_cause_summary=_extract_context(evidence[0], SUMMARIES[layer]),
                cited_evidence=evidence[:3],
                confidence=0.95,
                suggested_remediation=REMEDIATIONS[layer],
            )

    fallback_line = next(
        (line for line in raw_trace.split("\n") if "ERROR" in line.upper() or "FATAL" in line.upper()),
        raw_trace.split("\n")[0] if raw_trace else "ERROR: unknown failure",
    )
    fallback_summary = _extract_context(fallback_line, "Unclassified failure defaulting to tool/schema contract layer.")
    return TriageDiagnosis(
        layer=FailureLayer.L1_TOOL_AND_SCHEMA_CONTRACTS,
        root_cause_summary=fallback_summary,
        cited_evidence=[fallback_line],
        confidence=0.5,
        suggested_remediation=REMEDIATIONS[FailureLayer.L1_TOOL_AND_SCHEMA_CONTRACTS],
    )


def triage_agent_node(state: TriageState) -> Dict[str, Any]:
    feedback = state.get("feedback")
    diagnosis = _classify_trace(state["raw_trace"], feedback)
    return {"diagnosis": diagnosis.model_dump()}


def verifier_node(state: TriageState) -> Dict[str, Any]:
    diagnosis = state.get("diagnosis")
    if not diagnosis:
        return {
            "is_verified": False,
            "unverified_snippets": ["No diagnosis provided."],
            "feedback": "Grounding failure: No diagnosis extracted. Re-extract character-accurate substrings.",
            "retries": state.get("retries", 0) + 1,
        }

    cited = diagnosis.get("cited_evidence", [])
    passed, unverified = verify_evidence(state["raw_trace"], cited)

    if passed:
        return {"is_verified": True, "unverified_snippets": []}

    feedback = (
        f"CRITICAL GROUNDING FAILURE: The cited snippets were NOT found verbatim in the raw trace: "
        f"{unverified}. You have hallucinated this evidence. Re-evaluate the trace and extract EXACT character-accurate substrings. Do not summarize."
    )
    return {
        "is_verified": False,
        "unverified_snippets": unverified,
        "feedback": feedback,
        "retries": state.get("retries", 0) + 1,
    }


def reflection_node(state: TriageState) -> Dict[str, Any]:
    feedback = state.get("feedback", "Reviewing extraction mismatch.")
    logs = state.get("reflection_logs", [])
    step = state.get("retries", 1)
    
    thought = f"[Attempt {step}] Reflection Engine Triggered.\nFeedback: {feedback}\nAction: Re-evaluating trace substrings."
    
    return {
        "reflection_logs": logs + [thought],
        "reflection_executed": True
    }


def _route_after_verify(state: TriageState) -> str:
    if state.get("is_verified"):
        return END
    if state.get("retries", 0) >= 3:
        return END
    return "reflection_node"


def build_pipeline():
    workflow = StateGraph(TriageState)
    workflow.add_node("triage_agent_node", triage_agent_node)
    workflow.add_node("verifier_node", verifier_node)
    workflow.add_node("reflection_node", reflection_node)

    workflow.set_entry_point("triage_agent_node")
    workflow.add_edge("triage_agent_node", "verifier_node")
    workflow.add_conditional_edges(
        "verifier_node",
        _route_after_verify,
        {"reflection_node": "reflection_node", END: END},
    )
    workflow.add_edge("reflection_node", "triage_agent_node")
    return workflow.compile()


def run_triage_pipeline(raw_trace: str, pruned_trace: str) -> Dict[str, Any]:
    pipeline = build_pipeline()
    initial_state: TriageState = {
        "raw_trace": raw_trace,
        "pruned_trace": pruned_trace,
        "diagnosis": None,
        "retries": 0,
        "feedback": None,
        "is_verified": False,
        "unverified_snippets": [],
        "reflection_logs": [],
        "reflection_executed": False,
    }
    return pipeline.invoke(initial_state)
