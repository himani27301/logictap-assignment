<div align="center">

# Logictap · Call Webhooks
### Repeated deliveries. One stored record.

A small, inspectable webhook service built with **Python + SQLite**.  
Accept call-ended events, retain the first valid record, and acknowledge retries safely.

![Python](https://img.shields.io/badge/Python-standard_library-3776AB?style=flat-square&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-persistent_storage-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Dependencies](https://img.shields.io/badge/Dependencies-zero_packages-16836B?style=flat-square)

[Implementation](app.py) · [Original version](app_v1.py) · [Tests](test_app.py) · [Execution evidence](proof.txt) · [AI prompts](prompts.md)

</div>

---

> **Core guarantee:** one stored row per `call_id`. A valid repeated request returns HTTP 200 without inserting or replacing the record.

## At a glance

| Accept | Deduplicate | Retrieve |
| :--- | :--- | :--- |
| Validate JSON call-ended messages | Enforce uniqueness inside SQLite | Return the original stored record |
| Clear errors for invalid input | Preserve data across restarts | JSON 404 for an unknown call |

Built for the Logictap engineering assessment by **Himani Naidu**, with AI assistance documented in [prompts.md](prompts.md).

## Run in a minute

No package installation is required. The recorded environment is **Python 3.12.14 / SQLite 3.53.1**; see [environment.txt](environment.txt).

```bash
git clone https://github.com/himani27301/logictap-assignment.git
cd logictap-assignment
python app.py
```

The service listens on **http://127.0.0.1:8000** and stores records in `calls.db`. On Windows, use `py` if `python` is unavailable. Press **Ctrl+C** to stop it.

In a second terminal, run the tests:

```bash
python -m unittest -v test_app.py
```

<details>
<summary><strong>Try it from Windows PowerShell</strong></summary>

```powershell
$body = '{"call_id":"abc123","status":"answered","duration_secs":42}'
Invoke-RestMethod http://127.0.0.1:8000/call-ended -Method Post -ContentType 'application/json' -Body $body
Invoke-RestMethod http://127.0.0.1:8000/call-ended -Method Post -ContentType 'application/json' -Body $body
Invoke-RestMethod http://127.0.0.1:8000/calls/abc123
```

</details>

<details>
<summary><strong>Try it from Bash / curl</strong></summary>

With the service running, execute `bash proof.sh`, or use:

```bash
BODY='{"call_id":"abc123","status":"answered","duration_secs":42}'
curl -sS http://127.0.0.1:8000/call-ended -H 'Content-Type: application/json' -d "$BODY"
curl -sS http://127.0.0.1:8000/call-ended -H 'Content-Type: application/json' -d "$BODY"
curl -sS http://127.0.0.1:8000/calls/abc123
```

</details>

On a fresh database, the responses are:

```json
{"ok": true, "duplicate": false}
{"ok": true, "duplicate": true}
{"call_id": "abc123", "status": "answered", "duration_secs": 42}
```

All three requests return **HTTP 200**. If `abc123` already exists, both POSTs are duplicates. To use another database, set `CALLS_DB` to a new file path before starting the server.

## API contract

| Request | Result | HTTP |
| :--- | :--- | :---: |
| `POST /call-ended` · new valid ID | Store the record; `duplicate: false` | 200 |
| `POST /call-ended` · existing valid ID | Keep the first record; `duplicate: true` | 200 |
| `GET /calls/abc123` · known ID | Return the stored JSON | 200 |
| `GET /calls/abc123` · unknown ID | `{"error": "Call not found"}` | 404 |
| POST with missing/invalid fields or malformed JSON | Clear JSON error; no insert | 400 |
| POST with the wrong content type | `{"error": "Use application/json"}` | 415 |
| Database operation fails | Retriable storage error | 503 |

**Validation:** the body must be a JSON object; `call_id` and `status` must be nonempty strings; `duration_secs` must be a nonnegative integer, excluding booleans. POST bodies are limited to 65,536 bytes.

**Duplicate policy:** the first valid record wins, even when a later valid request changes the duration or status. Validation happens before deduplication, so malformed retries are rejected.

## Why duplicates cannot create a second row

The database owns the uniqueness rule:

```sql
INSERT INTO calls (call_id, payload) VALUES (?, ?)
ON CONFLICT(call_id) DO NOTHING;
```

`call_id` is the primary key. The insertion and conflict decision happen together, avoiding a separate “check, then insert” race. Each request uses its own connection, commits before returning success, and explicitly closes the connection.

If the commit succeeds but the response is lost, a valid retry returns 200 without another row. This guarantees an **idempotent stored effect**; it does not promise exactly-once HTTP delivery or external actions.

## From first draft to final

| Area | Version 1 · preserved | Final implementation |
| :--- | :--- | :--- |
| Storage | In-memory dictionary | Persistent SQLite database |
| Duplicate handling | Dictionary `setdefault` | Primary key + atomic conflict handling |
| Invalid input | Minimal checks; malformed JSON unhandled | Type validation and structured HTTP errors |
| Connections | No database | Explicit commit/rollback and closure |
| Verification | Initial baseline | Real HTTP tests for repeats, concurrency and restart |

The [first AI-generated file](app_v1.py) is unchanged. Its SHA-256 is recorded in [environment.txt](environment.txt). The [prompt record](prompts.md) describes the actual iteration.

## Verification

**Eight automated tests passed in the execution workspace.** These are loopback HTTP tests against temporary databases, with direct row-count assertions where relevant.

| Test | What it checks |
| :--- | :--- |
| Repeated request | Two successful POSTs, one row, matching GET |
| 12 simultaneous deliveries | One insert, eleven duplicates, all HTTP 200 |
| Server restart | Stored record and duplicate recognition survive |
| Changed duplicate payload | Original record remains intact |
| Missing call ID | Clear 400 response; no insert |
| Malformed JSON | Clear 400 response; no insert |
| Invalid field types | Bad values rejected without storage |
| Unknown call | JSON 404 response |

[Captured terminal transcript](proof.txt) · [Original test output](test_output.txt) · [Standalone duplicate test](standalone_duplicate_test.py)

To rerun only the required standalone test:

```bash
python -m unittest -v standalone_duplicate_test.py
```

To regenerate the terminal demonstration, stop any server on port 8000 and run `python capture_proof.py`. It uses a temporary empty database and overwrites `proof.txt` with the new capture.

## Repository guide

| File | Purpose |
| :--- | :--- |
| [app.py](app.py) | Final service |
| [app_v1.py](app_v1.py) | Untouched first AI version |
| [test_app.py](test_app.py) | Eight-case HTTP test suite |
| [standalone_duplicate_test.py](standalone_duplicate_test.py) | Self-contained duplicate test |
| [proof.sh](proof.sh) / [proof.txt](proof.txt) | Local commands and captured responses |
| [capture_proof.py](capture_proof.py) | Reproducible terminal capture |
| [webhook_commands.sh](webhook_commands.sh) | Two original external webhook requests |
| [test_output.txt](test_output.txt) | Captured full test log |
| [prompts.md](prompts.md) | Prompts and AI iteration record |
| [environment.txt](environment.txt) | Runtime versions and baseline checksum |

## Scope and provenance

This is a local assessment service, bound to loopback. Production webhook signatures, TLS, rate limiting, migrations, monitoring and business retry scheduling are outside its scope. A production integration should distinguish a **call ID** from a **provider event ID** rather than deduplicating every event type by call ID.

ChatGPT/Codex generated and reviewed both versions and executed the requests and tests in its workspace. The submitted PDF contains the four-part answers and the real Webhook.site inbox screenshot. This repository does not claim execution on the candidate's laptop. The 12-client test checks a concurrency case; it is not a load benchmark.
