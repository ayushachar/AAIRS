import re
from typing import List

NOISE_PATTERNS = [
    re.compile(r"heartbeat", re.IGNORECASE),
    re.compile(r"healthcheck", re.IGNORECASE),
    re.compile(r"health.?check", re.IGNORECASE),
    re.compile(r"polling", re.IGNORECASE),
    re.compile(r"^\s*DEBUG:", re.IGNORECASE),
]

SIGNAL_KEYWORDS = [
    "ERROR",
    "EXCEPTION",
    "TRACEBACK",
    "FATAL",
    "FAIL",
    "TOOL",
    "HTTP 4",
    "HTTP 5",
    "429",
    "503",
    "JSON TRUNCATION",
    "TIMEOUT",
    "RETURN",
    "ASSISTANT",
    "USER",
]


def _is_noise(line: str) -> bool:
    return any(pattern.search(line) for pattern in NOISE_PATTERNS)


def _is_signal(line: str) -> bool:
    upper = line.upper()
    return any(keyword in upper for keyword in SIGNAL_KEYWORDS)


def prune_telemetry_trace(raw_trace: str, max_chars: int = 12000) -> str:
    """
    Filter polling heartbeats and healthchecks while preserving stack traces,
    error payloads, tool I/O, and boundary logs. Apply head/tail preservation
    when logs exceed token boundaries.
    """
    lines = raw_trace.split("\n")
    if not lines:
        return raw_trace

    total_lines = len(lines)
    boundary_count = max(1, total_lines // 10)
    optimized: List[str] = []
    keep_next = 0

    for i, line in enumerate(lines):
        if i < boundary_count or i >= total_lines - boundary_count:
            optimized.append(line)
            continue

        if _is_signal(line):
            optimized.append(line)
            keep_next = 5
            continue

        if keep_next > 0:
            optimized.append(line)
            keep_next -= 1
            continue

        if _is_noise(line):
            continue

        if "TOOL" in line.upper() or "RETURN" in line.upper():
            optimized.append(line)

    deduped: List[str] = []
    for line in optimized:
        if not deduped or deduped[-1] != line:
            deduped.append(line)

    result = "\n".join(deduped)

    if len(result) <= max_chars:
        return result

    head_size = int(max_chars * 0.6)
    tail_size = int(max_chars * 0.4)
    marker = "\n[... truncated ...]\n"
    head = result[:head_size]
    tail = result[-tail_size:]
    return head + marker + tail


def normalize_trace(raw_trace: str) -> str:
    """Backward-compatible alias for trace pruning."""
    return prune_telemetry_trace(raw_trace)
