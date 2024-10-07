import os
import sys
from pathlib import Path
from typing import NoReturn

import id  # pylint: disable=redefined-builtin
import requests


_GITHUB_STEP_SUMMARY = Path(os.getenv('GITHUB_STEP_SUMMARY'))

# The top-level error message that gets rendered.
# This message wraps one of the other templates/messages defined below.
_ERROR_SUMMARY_MESSAGE = """
Trusted publishing exchange failure:

{message}

You're seeing this because the action wasn't given the inputs needed to
perform password-based or token-based authentication. If you intended to
perform one of those authentication methods instead of trusted
publishing, then you should double-check your secret configuration and variable
names.
"""

# Rendered if OIDC identity token retrieval fails for any reason.
_TOKEN_RETRIEVAL_FAILED_MESSAGE = """
OpenID Connect token retrieval failed: {identity_error}

This generally indicates a workflow configuration error, such as insufficient
permissions. Make sure that your workflow has `id-token: write` configured
at the job level, e.g.:

```yaml
permissions:
  id-token: write
```

Learn more at https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect#adding-permissions-settings.
"""  # noqa: S105; not a password

# Rendered if the package index refuses the given OIDC token.
_SERVER_REFUSED_TOKEN_EXCHANGE_MESSAGE = """
Token request failed: the server refused the request for the following reasons:

{reasons}

This generally indicates a trusted publisher configuration error, but could
also indicate an internal error on GitHub or GitGuardian's part.

{rendered_claims}
"""  # noqa: S105; not a password

_RENDERED_CLAIMS = """
The claims rendered below are **for debugging purposes only**. You should **not**
use them to configure a trusted publisher unless they already match your expectations.

If a claim is not present in the claim set, then it is rendered as `MISSING`.

* `sub`: `{sub}`
* `repository`: `{repository}`
* `repository_owner`: `{repository_owner}`
* `repository_owner_id`: `{repository_owner_id}`
* `job_workflow_ref`: `{job_workflow_ref}`
* `ref`: `{ref}`
"""

# Rendered if the package index's token response isn't valid JSON.
_SERVER_TOKEN_RESPONSE_MALFORMED_JSON = """
Token request failed: the index produced an unexpected
{status_code} response.

This strongly suggests a server configuration or downtime issue; wait
a few minutes and try again.
"""  # noqa: S105; not a password

# Rendered if the package index's token response isn't a valid API token payload.
_SERVER_TOKEN_RESPONSE_MALFORMED_MESSAGE = """
Token response error: the index gave us an invalid response.

This strongly suggests a server configuration or downtime issue; wait
a few minutes and try again.
"""  # noqa: S105; not a password


def debug(msg: str):
    print(f'::debug::{msg.title()}', file=sys.stderr)


def die(msg: str) -> NoReturn:
    with _GITHUB_STEP_SUMMARY.open('a', encoding='utf-8') as io:
        print(_ERROR_SUMMARY_MESSAGE.format(message=msg), file=io)

    # HACK: GitHub Actions' annotations don't work across multiple lines naively;
    # translating `\n` into `%0A` (i.e., HTML percent-encoding) is known to work.
    # See: https://github.com/actions/toolkit/issues/193
    msg = msg.replace('\n', '%0A')
    print(f'::error::Trusted publishing exchange failure: {msg}', file=sys.stderr)
    sys.exit(1)


gitguardian_url = os.environ.get("GITGUARDIAN_INSTANCE")
if not gitguardian_url:
    die("Please set the GITGUARDIAN_INSTANCE environment variable.")

token_exchange_url = f"{gitguardian_url}/v1/oidc/get_token"
oidc_audience = "gitguardian"

print(f'selected trusted publishing exchange endpoint: {token_exchange_url}', file=sys.stderr)

try:
    oidc_token = id.detect_credential(audience=oidc_audience)
except id.IdentityError as identity_error:
    for_cause_msg = _TOKEN_RETRIEVAL_FAILED_MESSAGE.format(identity_error=identity_error)
    die(for_cause_msg)

# Now we can do the actual token exchange.
mint_token_resp = requests.post(
    token_exchange_url,
    json={'token': oidc_token},
    timeout=5,  # S113 wants a timeout
)

try:
    mint_token_payload = mint_token_resp.json()
except requests.JSONDecodeError:
    print(mint_token_resp.content, file=sys.stderr)
    # Token exchange failure normally produces a JSON error response, but
    # we might have hit a server error instead.
    die(
        _SERVER_TOKEN_RESPONSE_MALFORMED_JSON.format(
            status_code=mint_token_resp.status_code,
        ),
    )

# On failure, the JSON response includes the list of errors that
# occurred during minting.
if not mint_token_resp.ok:
    die(
        _SERVER_REFUSED_TOKEN_EXCHANGE_MESSAGE.format(
            reasons=mint_token_payload.get("detail", ""),
            rendered_claims="",
        ),
    )

gg_token = mint_token_payload.get('gg-token')
if gg_token is None:
    die(_SERVER_TOKEN_RESPONSE_MALFORMED_MESSAGE)

# This final print will be captured by the subshell in `twine-upload.sh`.
print(gg_token)
