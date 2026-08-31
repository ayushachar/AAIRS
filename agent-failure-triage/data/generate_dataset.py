import json
import os
import random

from src.schemas import FailureLayer

LAYER_PREFIX_TO_ENUM = {
    "L1": FailureLayer.L1_TOOL_AND_SCHEMA_CONTRACTS,
    "L2": FailureLayer.L2_RETRIEVAL_AND_RAG,
    "L3": FailureLayer.L3_INFRASTRUCTURE_AND_EXTERNAL_APIS,
    "L4": FailureLayer.L4_CONTEXT_WINDOW_AND_TOKEN_LIMITS,
    "L5": FailureLayer.L5_ORCHESTRATION_AND_ROUTING,
    "L6": FailureLayer.L6_RETRY_LOGIC_AND_SIDE_EFFECTS,
    "L7": FailureLayer.L7_MODEL_BEHAVIOR_AND_PROMPT_DRIFT,
    "L8": FailureLayer.L8_STATE_CACHE_AND_CONCURRENCY,
}

TEMPLATES = {
    "L1": [
        "TOOL CALL: retrieve_db",
        "Exception: Schema mismatch in user_id, expected int got string.",
        "FATAL: Tool contract violated.",
        "ERROR: Missing key 'payload' in tool response.",
        "WARN: Enum drift detected in status field.",
    ],
    "L2": [
        "Searching vector DB... semantic drift detected.",
        "Chunk boundary truncation in retrieved context.",
        "ERROR: Evidence not found due to RAG failure.",
        "WARN: Stale index returned outdated document.",
        "ERROR: Empty context threshold triggered.",
    ],
    "L3": [
        "HTTP 429 Too Many Requests from dependency agent.",
        "Gateway Timeout reached on downstream service.",
        "FATAL: Infrastructure connection timeout.",
        "ERROR: Bearer token expired on upstream API.",
        "ERROR: DB pool exhaustion on connection acquire.",
    ],
    "L4": [
        "Context length exceeded maximum allowed tokens.",
        "JSON truncation at character 4096.",
        "Exception: token overflow during chat completion.",
        "ERROR: Lost in the middle retrieval loss detected.",
    ],
    "L5": [
        "Agent routed to agent B, which routed to agent A.",
        "Recursive multi-agent routing loop detected.",
        "ERROR: Orchestration missing explicit fallbacks.",
        "WARN: Intent misclassification routed to wrong specialist.",
    ],
    "L6": [
        "Retrying idempotent mutation after failure...",
        "Non-idempotent double mutation triggered on retry.",
        "Silent masking of duplicate document collision error.",
        "ERROR: Retry storm without exponential backoff.",
    ],
    "L7": [
        "Model issued safety refusal response due to guidelines.",
        "Delimiter breakage in system prompt parsing.",
        "FAIL: Model behavior generated malformed XML.",
        "WARN: Prompt injection via untrusted tool output.",
    ],
    "L8": [
        "Concurrency issue: thread A overwrites thread B context.",
        "Race condition on shared session memory.",
        "ERROR: Dirty cache hit corrupted state.",
        "WARN: Stale cache hit overriding fresh DB state.",
    ],
}


def generate():
    random.seed(42)
    traces = []
    layers = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]

    for i in range(50):
        layer = layers[i % 8]
        noise = [
            "DEBUG: heartbeat ok",
            "INFO: healthcheck passed",
            "DEBUG: polling agent status",
        ]
        trace_lines = [
            f"INFO: Starting telemetry capture for agent run {i}",
            "USER: Execute multi-step data processing pipeline",
            "ASSISTANT: Initializing workflow...",
            random.choice(noise),
        ] + random.sample(TEMPLATES[layer], min(3, len(TEMPLATES[layer]))) + [
            "ERROR: Workflow terminated unexpectedly.",
            f"INFO: End telemetry capture for agent run {i}",
        ]

        trace = "\n".join(trace_lines)
        traces.append(
            {
                "id": i,
                "raw_trace": trace,
                "expected_layer_prefix": layer,
                "expected_layer": LAYER_PREFIX_TO_ENUM[layer].value,
            }
        )

    output_dir = os.path.dirname(__file__)
    output_path = os.path.join(output_dir, "failure_traces.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2)

    print(f"Generated 50 synthetic golden cases at {output_path}")


if __name__ == "__main__":
    generate()
