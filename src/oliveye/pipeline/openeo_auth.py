"""Connect to openEO on the Copernicus Data Space Ecosystem, interactively or unattended.

Three ways to authenticate, tried in this order:

1. **Refresh token** (`OPENEO_REFRESH_TOKEN`): the personal account, unattended. The token is
   exported once from a machine where the browser login was done
   (`scripts/export_openeo_refresh_token.py`). It expires after a period of inactivity, so it
   must be exported again if a CI run reports an authentication error.
2. **Client credentials** (`OPENEO_CLIENT_ID` + `OPENEO_CLIENT_SECRET`): a service account.
   CDSE bills it separately until support links it to the personal account.
3. **Interactive** browser/device login (`authenticate_oidc`), the default on a laptop. The
   client stores the refresh token locally, so the browser is only needed now and then.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from openeo.rest.connection import connect

CDSE_URL = "openeo.dataspace.copernicus.eu"
CDSE_PROVIDER_ID = "CDSE"

ENV_CLIENT_ID = "OPENEO_CLIENT_ID"
ENV_CLIENT_SECRET = "OPENEO_CLIENT_SECRET"  # noqa: S105 - variable name, not a secret
ENV_REFRESH_TOKEN = "OPENEO_REFRESH_TOKEN"  # noqa: S105 - variable name, not a secret


def auth_method(env: Mapping[str, str] = os.environ) -> str:
    """Which authentication `connect_cdse` will use with the given environment."""
    # The personal account first: a service account is billed separately until CDSE links it.
    if env.get(ENV_REFRESH_TOKEN):
        return "refresh_token"
    if env.get(ENV_CLIENT_ID) and env.get(ENV_CLIENT_SECRET):
        return "client_credentials"
    return "interactive"


def connect_cdse(env: Mapping[str, str] = os.environ) -> Any:
    """Return an authenticated `openeo.Connection` to CDSE."""
    connection = connect(CDSE_URL)
    method = auth_method(env)
    if method == "client_credentials":
        return connection.authenticate_oidc_client_credentials(
            client_id=env[ENV_CLIENT_ID],
            client_secret=env[ENV_CLIENT_SECRET],
            provider_id=CDSE_PROVIDER_ID,
        )
    if method == "refresh_token":
        return connection.authenticate_oidc_refresh_token(
            refresh_token=env[ENV_REFRESH_TOKEN], provider_id=CDSE_PROVIDER_ID
        )
    if env.get("CI"):
        # A browser login would hang until the job times out: fail fast with a clear message.
        raise RuntimeError(
            f"No openEO credentials in CI. Set the {ENV_REFRESH_TOKEN} repository secret "
            "(scripts/export_openeo_refresh_token.py) or client credentials."
        )
    return connection.authenticate_oidc()
