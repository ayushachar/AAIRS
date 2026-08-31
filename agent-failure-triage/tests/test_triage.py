import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.schemas import FailureLayer, TriageDiagnosis, TriageRequest
from src.trace_normalizer import prune_telemetry_trace
from src.verifier import normalize_text, verify_evidence

client = TestClient(app)


def test_verifier_exact_match():
    trace = "Exception: Context length exceeded at line 42."
    cited = ["Context length exceeded"]
    verified, unverified = verify_evidence(trace, cited)
    assert verified is True
    assert unverified == []


def test_verifier_hallucinated():
    trace = "Exception: Connection timeout."
    cited = ["Exception: DB timeout."]
    verified, unverified = verify_evidence(trace, cited)
    assert verified is False
    assert unverified == ["Exception: DB timeout."]


def test_trace_normalizer():
    trace = "Header line\nDEBUG: heartbeat\nHEALTHCHECK OK\nERROR: Something broke\nFooter line"
    pruned = prune_telemetry_trace(trace)
    assert "heartbeat" not in pruned
    assert "HEALTHCHECK OK" not in pruned
    assert "Something broke" in pruned


def test_schema_valid_layer():
    data = {
        "layer": "L1_TOOL_AND_SCHEMA_CONTRACTS",
        "root_cause_summary": "Type mismatch",
        "cited_evidence": ["TypeError: int"],
        "confidence": 0.9,
        "suggested_remediation": "Fix schema"
    }
    diagnosis = TriageDiagnosis(**data)
    assert diagnosis.layer == FailureLayer.L1_TOOL_AND_SCHEMA_CONTRACTS


def test_fastapi_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fastapi_triage_basic():
    # Because LLM is used, this might be slow or require mock.
    # We will just test validation error if format is bad.
    response = client.post("/v1/triage", json={"raw_trace": 123})
    assert response.status_code == 422
