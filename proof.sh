#!/usr/bin/env bash
set -euxo pipefail
URL=http://127.0.0.1:8000
BODY='{"call_id":"abc123","status":"answered","duration_secs":42}'
curl --fail-with-body -sS -w '\nHTTP %{http_code}\n' "$URL/call-ended" -H 'Content-Type: application/json' -d "$BODY"
curl --fail-with-body -sS -w '\nHTTP %{http_code}\n' "$URL/call-ended" -H 'Content-Type: application/json' -d "$BODY"
curl --fail-with-body -sS -w '\nHTTP %{http_code}\n' "$URL/calls/abc123"
