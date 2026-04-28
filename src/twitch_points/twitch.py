from __future__ import annotations

import httpx

GQL_URL = "https://gql.twitch.tv/gql"
# Public web Client-ID — the only one that pairs with browser auth-tokens.
WEB_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

# Hash of the canonical ChannelPointsContext operation as shipped by Twitch's
# web client. Using persistedQuery (no raw query body) lets Twitch resolve the
# operation server-side, which is more robust to schema changes than embedding
# our own query string. This same hash is used by TwitchChannelPointsMiner and
# similar tools; if Twitch ever rotates it we'll get a "PersistedQueryNotFound"
# error and need to refresh from a browser network capture.
CHANNEL_POINTS_PERSISTED_HASH = (
    "1530a003a7d374b0380b79db0be0534f30ff46e61cffa2bc0e2468a909fbc024"
)


class TwitchError(Exception):
    """Base class for Twitch GQL failures."""


class TwitchAuthError(TwitchError):
    """Token is missing, expired, or otherwise rejected."""


class TwitchChannelNotFound(TwitchError):
    """Channel login does not exist."""


class TwitchClient:
    def __init__(self, oauth_token: str, *, timeout: float = 10.0) -> None:
        if not oauth_token:
            raise TwitchAuthError("TWITCH_OAUTH_TOKEN is empty")
        self._client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"OAuth {oauth_token}",
                "Client-ID": WEB_CLIENT_ID,
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> TwitchClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get_balance(self, channel_login: str) -> int:
        payload = {
            "operationName": "ChannelPointsContext",
            "variables": {"channelLogin": channel_login},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": CHANNEL_POINTS_PERSISTED_HASH,
                }
            },
        }
        resp = self._client.post(GQL_URL, json=payload)
        if resp.status_code == 401:
            raise TwitchAuthError(f"401 Unauthorized fetching balance for {channel_login}")
        resp.raise_for_status()
        body = resp.json()

        if errors := body.get("errors"):
            msg = "; ".join(e.get("message", "?") for e in errors)
            lower = msg.lower()
            if "persistedquerynotfound" in lower.replace(" ", ""):
                raise TwitchError(
                    "Persisted query hash rejected by Twitch — the hash in twitch.py "
                    "is stale. Re-capture ChannelPointsContext from the Twitch website "
                    "(DevTools → Network → look for the gql request) and update "
                    "CHANNEL_POINTS_PERSISTED_HASH."
                )
            if "auth" in lower:
                raise TwitchAuthError(msg)
            raise TwitchError(f"GQL errors for {channel_login}: {msg}")

        community = (body.get("data") or {}).get("community")
        if community is None:
            raise TwitchChannelNotFound(f"Unknown channel: {channel_login}")
        channel = community.get("channel") or {}
        self_ = channel.get("self")
        if self_ is None:
            raise TwitchAuthError(
                f"No 'self' in response for {channel_login} — token likely invalid"
            )
        points = self_.get("communityPoints")
        if not points:
            raise TwitchError(f"Channel {channel_login} has no community points configured")
        balance = points.get("balance")
        if balance is None:
            raise TwitchError(f"Missing balance in response for {channel_login}")
        return int(balance)
