from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FailureLayer(str, Enum):
    L1_TOOL_AND_SCHEMA_CONTRACTS = "L1_TOOL_AND_SCHEMA_CONTRACTS"
    L2_RETRIEVAL_AND_RAG = "L2_RETRIEVAL_AND_RAG"
    L3_INFRASTRUCTURE_AND_EXTERNAL_APIS = "L3_INFRASTRUCTURE_AND_EXTERNAL_APIS"
    L4_CONTEXT_WINDOW_AND_TOKEN_LIMITS = "L4_CONTEXT_WINDOW_AND_TOKEN_LIMITS"
    L5_ORCHESTRATION_AND_ROUTING = "L5_ORCHESTRATION_AND_ROUTING"
    L6_RETRY_LOGIC_AND_SIDE_EFFECTS = "L6_RETRY_LOGIC_AND_SIDE_EFFECTS"
    L7_MODEL_BEHAVIOR_AND_PROMPT_DRIFT = "L7_MODEL_BEHAVIOR_AND_PROMPT_DRIFT"
    L8_STATE_CACHE_AND_CONCURRENCY = "L8_STATE_CACHE_AND_CONCURRENCY"


class TriageDiagnosis(BaseModel):
    layer: FailureLayer
    root_cause_summary: str
    cited_evidence: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_remediation: str


class TriageRequest(BaseModel):
    raw_trace: str
    session_id: Optional[str] = None


class TriageResponse(BaseModel):
    session_id: str
    is_verified: bool
    retries_used: int
    diagnosis: TriageDiagnosis
    pruned_token_count: int
    unverified_snippets: List[str]
