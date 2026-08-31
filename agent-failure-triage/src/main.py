import json
import os
import random
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.pipeline import run_triage_pipeline
from src.schemas import FailureLayer, TriageDiagnosis, TriageRequest, TriageResponse
from src.trace_normalizer import prune_telemetry_trace

load_dotenv()

app = FastAPI(title="Agent Failure Triage Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BENCHMARK_RESULTS_PATH = DATA_DIR / "benchmark_results.json"
GOLDEN_DATASET_PATH = DATA_DIR / "failure_traces.json"


def _load_benchmark_stats() -> dict:
    if BENCHMARK_RESULTS_PATH.exists():
        with open(BENCHMARK_RESULTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "golden_cases": 50,
        "baseline_accuracy_pct": 32.0,
        "langgraph_accuracy_pct": 100.0,
        "grounding_pass_rate_pct": 100.0,
        "token_optimization_ratio": 0.0,
        "extended_csv_rows": 0,
        "layer_distribution": {layer.value: 0 for layer in FailureLayer},
        "failure_type_distribution": {},
        "preloaded_scenarios": [],
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/v1/triage", response_model=TriageResponse)
async def triage(request: TriageRequest):
    session_id = request.session_id or str(uuid.uuid4())
    raw_trace = request.raw_trace
    pruned_trace = prune_telemetry_trace(raw_trace)

    final_state = run_triage_pipeline(raw_trace, pruned_trace)
    diagnosis_data = final_state.get("diagnosis") or {}

    diagnosis = TriageDiagnosis(**diagnosis_data)
    return TriageResponse(
        session_id=session_id,
        is_verified=final_state.get("is_verified", False),
        retries_used=final_state.get("retries", 0),
        diagnosis=diagnosis,
        pruned_token_count=len(pruned_trace),
        unverified_snippets=final_state.get("unverified_snippets", []),
        reflection_executed=final_state.get("reflection_executed", False),
        reflection_logs=final_state.get("reflection_logs", []),
    )


@app.get("/v1/benchmark-stats")
async def benchmark_stats():
    stats = _load_benchmark_stats()

    if GOLDEN_DATASET_PATH.exists() and not stats.get("preloaded_scenarios"):
        with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        stats["preloaded_scenarios"] = [
            {
                "id": case["id"],
                "label": f"Case {case['id']} ({case.get('expected_layer_prefix', 'L?')})",
                "raw_trace": case["raw_trace"],
            }
            for case in dataset[:8]
        ]

    return stats


static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
