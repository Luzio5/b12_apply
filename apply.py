#!/usr/bin/env python3
import os
import sys
import json
import hmac
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone

B12_ENDPOINT = "https://b12.io/apply/submission"
SIGNING_SECRET = "hello-there-from-b12"


def iso8601_utc_now_ms() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def required_env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return val


def github_action_run_link() -> str:
    server = os.getenv("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    run_id = os.getenv("GITHUB_RUN_ID", "").strip()
    if repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    # Fallback for non-GitHub CI:
    return required_env("ACTION_RUN_LINK")


def github_repo_link() -> str:
    server = os.getenv("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    if repo:
        return f"{server}/{repo}"
    # Fallback for non-GitHub CI:
    return required_env("REPOSITORY_LINK")


def main() -> None:
    name = "Luciano Almenares"
    email = required_env("B12_EMAIL")

    # Default LinkedIn unless overridden
    resume_link = "https://www.linkedin.com/in/luciano-almenares/"

    repository_link = os.getenv("B12_REPOSITORY_LINK", "").strip() or github_repo_link()
    action_run_link = os.getenv("B12_ACTION_RUN_LINK", "").strip() or github_action_run_link()

    payload = {
        "timestamp": iso8601_utc_now_ms(),
        "name": name,
        "email": email,
        "resume_link": resume_link,
        "repository_link": repository_link,
        "action_run_link": action_run_link,
    }

    body_str = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    body_bytes = body_str.encode("utf-8")

    digest = hmac.new(SIGNING_SECRET.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    signature = f"sha256={digest}"

    req = urllib.request.Request(
        B12_ENDPOINT,
        data=body_bytes,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Signature-256": signature,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            if resp.status != 200:
                print(f"HTTP {resp.status}: {resp_body}", file=sys.stderr)
                sys.exit(1)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"HTTPError {e.code}: {err_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(resp_body)
    except json.JSONDecodeError:
        print(f"Non-JSON response: {resp_body}", file=sys.stderr)
        sys.exit(1)

    receipt = data.get("receipt")
    if not data.get("success") or not receipt:
        print(f"Unexpected response: {resp_body}", file=sys.stderr)
        sys.exit(1)

    print(receipt)


if __name__ == "__main__":
    main()
