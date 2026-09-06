import httpx
import logging

logger = logging.getLogger(__name__)

async def dispatch_to_ao(trace_id: str, error_type: str, grounding_score: float) -> dict:
    """
    Dispatches triage telemetry to the AO decentralized network.
    """
    url = "https://mu.ao-testnet.xyz"
    payload = {
        "Target": "aairs-sre-telemetry-process",
        "Tags": [
            {"name": "App-Name", "value": "AAIRS"},
            {"name": "Action", "value": "Triage-Report"},
            {"name": "TraceID", "value": str(trace_id)},
            {"name": "ErrorType", "value": str(error_type)},
            {"name": "GroundingScore", "value": str(grounding_score)}
        ],
        "Data": f"AAIRS verified diagnostic report for trace {trace_id}"
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

        return {"ao_logged": True, "gateway": "mu.ao-testnet.xyz"}
    except Exception as e:
        logger.error(f"Failed to dispatch to AO: {e}")
        return {"ao_logged": False}
