import pytest

from twitch_points.twitch import (
    GQL_URL,
    TwitchAuthError,
    TwitchChannelNotFound,
    TwitchClient,
    TwitchError,
)


def test_get_balance_success(httpx_mock):
    httpx_mock.add_response(
        url=GQL_URL,
        json={
            "data": {
                "community": {
                    "channel": {"self": {"communityPoints": {"balance": 12345}}}
                }
            }
        },
    )
    with TwitchClient("fake-token") as c:
        assert c.get_balance("xqc") == 12345


def test_channel_not_found(httpx_mock):
    httpx_mock.add_response(url=GQL_URL, json={"data": {"community": None}})
    with TwitchClient("fake-token") as c, pytest.raises(TwitchChannelNotFound):
        c.get_balance("nonexistent")


def test_self_null_means_auth(httpx_mock):
    httpx_mock.add_response(
        url=GQL_URL,
        json={"data": {"community": {"channel": {"self": None}}}},
    )
    with TwitchClient("fake-token") as c, pytest.raises(TwitchAuthError):
        c.get_balance("xqc")


def test_401_is_auth_error(httpx_mock):
    httpx_mock.add_response(url=GQL_URL, status_code=401, json={})
    with TwitchClient("fake-token") as c, pytest.raises(TwitchAuthError):
        c.get_balance("xqc")


def test_no_community_points_configured(httpx_mock):
    httpx_mock.add_response(
        url=GQL_URL,
        json={
            "data": {
                "community": {"channel": {"self": {"communityPoints": None}}}
            }
        },
    )
    with TwitchClient("fake-token") as c, pytest.raises(TwitchError):
        c.get_balance("xqc")


def test_empty_token_rejected():
    with pytest.raises(TwitchAuthError):
        TwitchClient("")
