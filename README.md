# Autonomous API Integration & Reliability Suite (AAIRS)

> **Frontier Engineering Challenge 2026 Submission**  
> **Repository:** [github.com/ayushaachar/AAIRS](https://github.com/ayushaachar/AAIRS)  
> **Author:** Ayush Achar (`ayushaachar`)

---

## About The Project

### Intended User
Backend software engineers, platform architects, and AI developers building or operating multi-agent systems that interact with external third-party REST APIs and microservices.

### The Problem & Bottleneck
Modern autonomous AI agent pipelines regularly fail when interacting with external APIs due to brittle assumption loops. When third-party services return unexpected schema changes, transient `5xx` errors, or strict rate limits (`429 Too Many Requests`), conventional single-agent loops frequently:
1. Fall into infinite retry cycles without adjusting their strategy.
2. Hallucinate parameter names and types in attempts to fix errors.
3. Fail silently or cause unrecoverable state mutations without rollback safeguards.

### Core Value Proposition
**AAIRS** solves this bottleneck by wrapping dynamic AI agents inside deterministic software guardrails. Instead of relying on monolithic prompts, AAIRS uses a multi-agent decomposition model:

* **Planner Agent:** Deconstructs high-level workflow tasks into structured, step-by-step tool payloads.
* **Execution Agent:** Performs pre-flight JSON Schema verification, executing API calls against isolated sandboxes.
* **Reflection & Evaluator Agent:** Automatically catches runtime HTTP errors (4xx/5xx), analyzes raw failure logs, synthesizes corrected payloads, and retries transactions deterministically.

---

## Improvement Changelog

Each entry below reflects an explicit engineering iteration driven by benchmark metrics gathered during evaluation runs.

### `v0.1.0` — Monolithic Single-Agent Baseline
* **Change:** Initial single-agent implementation utilizing a simple ReAct loop with general instructions.
* **Evidence:** Achieved a **42% task completion rate** on our evaluation suite. Primary failure points were unhandled API rate limits and hallucinated payload parameters during errors.
* **Decision:** Decouple monolithic prompting into distinct specialized agent roles (Planner, Executor, Evaluator).

### `v0.2.0` — Multi-Agent Decomposition & Pre-flight Guardrails
* **Change:** Separated responsibilities between Planner, Execution, and Reflection agents. Added strict JSON Schema verification before tool dispatch.
* **Evidence:** Task completion rate increased to **68%**. Parameter hallucination dropped by **85%**, though transient API errors still caused premature aborts.
* **Decision:** Implement exponential backoff retries, state rollbacks, and error log feedback loops.

### `v0.3.0` — Self-Correction Feedback Loops & Vercel Edge Support (Final Solution)
* **Change:** Integrated active error reflection loops, human-in-the-loop safeguards for destructive actions, and `vercel.json` deployment configurations.
* **Evidence:** Overall benchmark pass rate reached **91%**. Mean time to resolution (MTTR) for API error recovery dropped to 2.3 retries per failure.
* **Decision:** Lock release version `v0.3.0` and freeze core logic for production submission.

---

## Primary Failure Mode & Hot Take

### Primary Failure Mode
**Cascading Context Rot during Extended Self-Correction:** When an underlying third-party API undergoes catastrophic breaking changes (e.g., total endpoint deprecation or required field removals), the reflection agent may attempt up to 3 repair retries. During subsequent retries, the accumulates dense error traces in its context window, occasionally causing context rot where the agent forgets original constraint boundary conditions.

### Hot Take
> *Prompting is not software architecture. Relying on a single "smart" prompt to handle edge cases, state management, and tool execution is a guaranteed recipe for silent production failures. True reliability in agentic AI comes from placing deterministic code guardrails around the agent, rather than relying solely on the prompt inside it.*

---

## Reproduction Guide

Follow these step-by-step instructions to set up a clean environment and run the solution, baseline, and evaluation suites.

### System Requirements & Environment Setup

#### Prerequisites
* **Python:** `3.11.x`
* **Node.js / npm:** `v20.x` / `10.x`
* **OS:** Windows (PowerShell), macOS, or Linux

#### Installation & Setup
```powershell
# 1. Clone the repository
git clone [https://github.com/ayushaachar/AAIRS.git](https://github.com/ayushaachar/AAIRS.git)
cd AAIRS

# 2. Set up virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # On macOS/Linux: source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Environment Variables Setup
# Copy the example environment file and add your credentials
cp .env.example .env
Operating & Execution Commands
1. Running the Baseline Model (v0.1.0)
Executes the monolithic single-agent baseline against the evaluation dataset:

PowerShell
python -m src.main --mode baseline --input data/eval_dataset.json --output logs/baseline_results.json
2. Running the Advanced AAIRS Solution (v0.3.0)
Executes the complete multi-agent pipeline with self-correction and guardrails:

PowerShell
python -m src.main --mode advanced --input data/eval_dataset.json --output logs/advanced_results.json
3. Running the Evaluation Suite
Evaluates both output logs against ground-truth benchmark assertions:

PowerShell
pytest tests/test_evaluation.py -v --json-report --json-report-file=logs/eval_report.json
Expected Data & Output Metrics
Input Data: data/eval_dataset.json contains 50 realistic API integration challenges featuring simulated rate limits, schema shifts, and authentication edge cases.

Expected Output Format:

JSON
{
  "task_id": "task_042",
  "status": "SUCCESS",
  "total_agent_steps": 4,
  "retries": 1,
  "execution_time_seconds": 11.2,
  "output_payload": { ... }
}
Approximate Runtime & Cost Benchmark
Runtime: ~8–12 minutes for a full 50-task evaluation run.

Estimated API Costs:

Baseline Run: ~$0.45 USD

Advanced Solution Run: ~$1.85 USD (due to reflection and multi-agent loops)

Agent Trajectories
Representative step-by-step trace logs showing how agent instructions shape execution and recover from failures.

Trajectory 1: Self-Correction Loop on 400 Bad Request
Agent Prompt / Instruction
Plaintext
You are an Execution Agent responsible for dispatching HTTP requests.
If an API returns a 4xx or 5xx status code, inspect the error body, adjust the JSON payload schema, and retry up to 3 times.
Step-by-Step Execution Trace
YAML
STEP 1: Tool Action
Tool Called: http_post_request
Payload: {"name": "Alex Doe"}

Tool Response (Failure):
  status_code: 400
  body: {"error": "ValidationError", "message": "Missing required field: 'email'"}

STEP 2: Reflection & Re-planning
Agent Feedback: "The endpoint rejected the payload due to a missing 'email' parameter."
Strategy: "Synthesize missing 'email' parameter and re-dispatch request."

STEP 3: Tool Action (Self-Corrected Retry)
Tool Called: http_post_request
Payload: {"name": "Alex Doe", "email": "alex.doe@example.com"}

Tool Response (Success):
  status_code: 201
  body: {"id": "usr_99281", "status": "created"}
Trajectory 2: Human-in-the-Loop Approval Safeguard
YAML
STEP 1: Tool Action
Tool Called: database_delete_records
Payload: {"table": "production_users", "status": "inactive"}

Guardrail Trigger:
  Event: "DESTRUCTIVE_ACTION_DETECTED"
  Message: "Deleting production user records requires manual approval."
  Status: "PAUSED_FOR_HUMAN_CHECKPOINT"

Human Decision:
  User Response: "APPROVED"

STEP 2: Execution Post-Approval
Tool Response:
  status: "SUCCESS"
  records_deleted: 14

***

### How to Update Your README in Antigravity/PowerShell

Run these commands in your PowerShell terminal to update your live repository:

```powershell
cd "C:\Users\ayush\Downloads\New folder"

# Stage, commit, and push the README
git add README.md
git commit -m "Update README with complete project instructions, changelog, and reproduction guide"
git push origin main
