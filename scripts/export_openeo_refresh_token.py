"""One-time helper: copy your openEO refresh token into a GitHub Actions secret.

Run it on the computer where you already logged in to openEO in the browser:

    uv run python scripts/export_openeo_refresh_token.py

If the GitHub CLI (`gh`) is installed and logged in, the token is stored directly as the
repository secret OPENEO_REFRESH_TOKEN and never printed. Otherwise the script tells you where to
paste it by hand (GitHub → Settings → Secrets and variables → Actions → New repository secret).
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from openeo.rest.auth.config import RefreshTokenStore

CDSE_ISSUER_HINT = "dataspace.copernicus.eu"
SECRET_NAME = "OPENEO_REFRESH_TOKEN"  # noqa: S105 - secret name, not a secret


def find_cdse_refresh_token() -> str:
    """Return the most recently stored refresh token for the CDSE identity provider."""
    store = RefreshTokenStore()
    data: dict[str, dict[str, dict[str, str]]] = store.load()
    candidates = [
        entry
        for issuer, clients in data.items()
        if CDSE_ISSUER_HINT in issuer
        for entry in clients.values()
        if entry.get("refresh_token")
    ]
    if not candidates:
        sys.exit(
            f"No CDSE refresh token found in {store.path}. Log in once first:\n"
            '  uv run python -c "import openeo; '
            "openeo.connect('openeo.dataspace.copernicus.eu').authenticate_oidc()\""
        )
    latest = max(candidates, key=lambda entry: entry.get("date", ""))
    return latest["refresh_token"]


def main() -> None:
    token = find_cdse_refresh_token()
    gh = shutil.which("gh")
    if gh is None:
        print("GitHub CLI not found. Add this value by hand as the repository secret")
        print(f"{SECRET_NAME} (GitHub → Settings → Secrets and variables → Actions):\n")
        print(token)
        return
    subprocess.run([gh, "secret", "set", SECRET_NAME], input=token, text=True, check=True)
    print(f"Stored {SECRET_NAME} in the GitHub repository secrets (value not shown).")


if __name__ == "__main__":
    main()
