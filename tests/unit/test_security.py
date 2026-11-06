"""Security boundaries: configuration, private logs, and per-account throttling."""

import json
import logging

import pytest

from telegram_innovation.core.config import Config
from telegram_innovation.observability.logging import JSONFormatter, configure
from telegram_innovation.security.identity import participant_key
from telegram_innovation.security.ratelimit import RateLimiter

TOKEN = "123456:" + "A" * 35
SECRET = "a1" * 32


@pytest.fixture
def valid_env(monkeypatch):
    for name in (
        "BOT_TOKEN",
        "IDENTITY_SECRET",
        "DATABASE_PATH",
        "LOG_LEVEL",
        "LOG_FILE",
        "RETENTION_DAYS",
        "ADMIN_IDS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("IDENTITY_SECRET", SECRET)
    return monkeypatch


def test_config_accepts_valid_settings_without_secrets_in_repr(valid_env):
    valid_env.setenv("ADMIN_IDS", "12, 34")
    config = Config.from_env()
    assert config.admin_ids == frozenset({12, 34})
    assert config.retention_days == 7
    assert config.secret == bytes.fromhex(SECRET)
    assert TOKEN not in repr(config)
    assert SECRET not in repr(config)


@pytest.mark.parametrize(
    "name,value",
    [
        ("BOT_TOKEN", ""),
        ("BOT_TOKEN", "not-a-token"),
        ("IDENTITY_SECRET", "short"),
        ("IDENTITY_SECRET", "z" * 64),
        ("LOG_LEVEL", "NOISY"),
        ("RETENTION_DAYS", "0"),
        ("RETENTION_DAYS", "91"),
        ("RETENTION_DAYS", "NaN"),
        ("ADMIN_IDS", "-1"),
        ("ADMIN_IDS", "hello"),
        ("DATABASE_PATH", ":memory:"),
        ("DATABASE_PATH", ""),
    ],
)
def test_invalid_environment_fails_safely(valid_env, name, value):
    valid_env.setenv(name, value)
    with pytest.raises(ValueError) as error:
        Config.from_env()
    assert TOKEN not in str(error.value)
    assert SECRET not in str(error.value)


def test_logs_discard_raw_message_identifiers_credentials_and_exception():
    try:
        raise RuntimeError(f"request URL /bot{TOKEN}/sendMessage")
    except RuntimeError:
        import sys

        exc_info = sys.exc_info()
    record = logging.LogRecord(
        "test", logging.ERROR, __file__, 1, "private content %s", (TOKEN,), exc_info
    )
    record.event = "api_failure"
    record.operation = "sendMessage"
    record.correlation = "random-correlation"
    record.chat_id = -10012345
    record.user_id = 123456
    record.token = TOKEN
    record.secret = SECRET
    record.message = "sensitive message"
    rendered = JSONFormatter().format(record)
    result = json.loads(rendered)
    assert result["event"] == "api_failure"
    assert result["correlation"] == "random-correlation"
    for forbidden in (
        TOKEN,
        SECRET,
        "private content",
        "sensitive message",
        "-10012345",
        "123456",
        "RuntimeError",
    ):
        assert forbidden not in rendered
    assert "chat_id" not in result
    assert "user_id" not in result


def test_rotating_file_logs_are_bounded_and_http_logs_disabled(tmp_path):
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    http_states = {name: logging.getLogger(name).disabled for name in ("httpx", "httpcore")}
    try:
        configure("DEBUG", str(tmp_path / "events.jsonl"))
        rotating = [h for h in root.handlers if hasattr(h, "maxBytes")]
        assert len(rotating) == 1
        assert rotating[0].maxBytes > 0
        assert rotating[0].backupCount > 0
        assert all(logging.getLogger(name).disabled for name in http_states)
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers[:] = original_handlers
        root.setLevel(original_level)
        for name, disabled in http_states.items():
            logging.getLogger(name).disabled = disabled


def test_rate_limiter_refills_and_bounds_memory():
    limiter = RateLimiter(capacity=2, refill=1.0, max_keys=3)
    assert limiter.allow("person", now=100)
    assert limiter.allow("person", now=100)
    assert not limiter.allow("person", now=100)
    assert not limiter.allow("person", now=100.5)
    assert limiter.allow("person", now=101)
    for i in range(10):
        limiter.allow(f"person-{i}", now=102)
    assert len(limiter.buckets) <= 3


def test_identity_is_deterministic_and_scoped_to_card_and_secret():
    secret = bytes.fromhex(SECRET)
    key = participant_key(secret, "card-a", 123456)
    assert len(key) == 64
    assert key == participant_key(secret, "card-a", 123456)
    assert key != participant_key(secret, "card-b", 123456)
    assert key != participant_key(secret, "card-a", 654321)
    assert key != participant_key(b"b" * 32, "card-a", 123456)
