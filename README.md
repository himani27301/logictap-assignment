# Logictap | Call-ended webhook service

Python standard library only. Tested on Python 3.12.14 / SQLite 3.53.1.

## Run on Windows
1. Extract this folder, open a terminal in it.
2. Run `py app.py` (or `python app.py`). Keep this terminal open.
3. In a second terminal run `py -m unittest -v test_app.py`.
4. In PowerShell, send the same payload twice, then GET it:

```powershell
$body = '{"call_id":"abc123","status":"answered","duration_secs":42}'
Invoke-RestMethod http://127.0.0.1:8000/call-ended -Method Post -ContentType 'application/json' -Body $body
Invoke-RestMethod http://127.0.0.1:8000/call-ended -Method Post -ContentType 'application/json' -Body $body
Invoke-RestMethod http://127.0.0.1:8000/calls/abc123
```

The first POST has duplicate=false, subsequent ones true. Both return HTTP 200. Records persist in calls.db. Use a fresh DB path via CALLS_DB if replaying the initial demonstration; don't delete real data to reset a demo. Ctrl+C stops the service.

On Bash: `python app.py`, then in another terminal `bash proof.sh`. `python capture_proof.py` starts its own temporary empty database, records proof.txt and stops; port 8000 must be free.

## Files
- app_v1.py: untouched first AI code; SHA-256 in environment.txt.
- app.py: final implementation; test_app.py: eight tests using real loopback HTTP.
- proof.sh / proof.txt: exact local commands and captured output.
- webhook_commands.sh: exact two remote requests from Part 2.
- test_output.txt: full eight-case test log, not just the summary.
- standalone_duplicate_test.py: self-contained required automated test.
- prompts.md: user prompts and honest iteration record.

## Contract and choices
POST /call-ended requires an object with a nonempty string call_id and status, and a nonnegative integer duration_secs. Booleans are rejected as durations. A valid repeated call_id returns 200 without updating the first record, even if other values differ. Invalid messages are rejected before deduplication. GET /calls/{call_id} returns the stored fields or JSON 404. Parameterized SQL prevents interpolation of user input.

SQLite enforces the unique call_id inside INSERT ... ON CONFLICT DO NOTHING. Each request gets its own connection; transactions commit before success and connections are explicitly closed. This protects the stored-row invariant under concurrent deliveries. It does not guarantee exactly-once HTTP delivery or external side effects.

Local scope: not a production server; no webhook signatures, TLS, rate limiting, migrations, metrics, or business retry scheduler. Those are not needed for the requested local service. If adding provider events, verify signatures and scope event identity by provider/event ID; don't deduplicate every event type by call_id.

## Evidence and provenance
ChatGPT/Codex generated and reviewed both versions and ran commands/tests in its execution workspace. Version 1 is preserved, not reconstructed. The report screenshot is from a real Webhook.site inbox. Candidate laptop execution and personal reflection should be verified by the candidate. The report uses the explicitly allowed pasted-code option; the public repository is https://github.com/himani27301/logictap-assignment.
