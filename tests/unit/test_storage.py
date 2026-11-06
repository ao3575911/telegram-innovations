"""Independent state transitions and persistence/permission boundaries."""

import sqlite3

import pytest

from telegram_innovation.security.identity import participant_key
from telegram_innovation.storage import DomainError, Store

SECRET = b"independent-storage-test-secret!!"
NOW = 1_800_000_000


@pytest.fixture
def store(tmp_path):
    value = Store(str(tmp_path / "cards.sqlite3"), SECRET)
    yield value
    value.close()


def create(store, **overrides):
    args = dict(
        update_id=101,
        chat_id=-100,
        user_id=17,
        title="Beach cleanup",
        target=2,
        deadline=NOW + 600,
        now=NOW,
    )
    args.update(overrides)
    return store.create(**args)


def test_join_leave_and_deadline_snapshot(store):
    card = create(store)
    assert (card.status, card.count) == ("OPEN", 0)
    assert store.vote(card.id, 17, True, -100, now=NOW).count == 1
    assert store.vote(card.id, 17, True, -100, now=NOW).count == 1
    assert store.vote(card.id, 18, True, -100, now=NOW).status == "READY"
    assert store.vote(card.id, 18, False, -100, now=NOW).status == "OPEN"
    assert store.vote(card.id, 18, False, -100, now=NOW).count == 1
    assert store.vote(card.id, 18, True, -100, now=NOW).status == "READY"
    assert store.tick(now=NOW + 600)[0].status == "MET"
    assert store.tick(now=NOW + 601) == []
    with pytest.raises(DomainError, match="closed"):
        store.vote(card.id, 19, True, -100, now=NOW + 601)


def test_deadline_rejects_vote_even_without_scheduler(store):
    card = create(store)
    with pytest.raises(DomainError, match="closed"):
        store.vote(card.id, 18, True, -100, now=card.deadline)
    assert store.tick(now=card.deadline)[0].status == "MISSED"


def test_create_duplicate_returns_same_card_after_deadline(store):
    first = create(store)
    second = create(store, now=NOW + 10000, title="Changed")
    assert first == second
    assert store.health()["cards"] == 1


def test_chat_binding_and_cancel_permissions(store):
    card = create(store)
    with pytest.raises(DomainError, match="unavailable"):
        store.vote(card.id, 17, True, -200, now=NOW)
    with pytest.raises(DomainError, match="creator"):
        store.cancel(card.id, 18, -100, now=NOW)
    with pytest.raises(DomainError, match="unavailable"):
        store.cancel(card.id, 18, -200, is_admin=True, now=NOW)
    assert store.cancel(card.id, 18, -100, is_admin=True, now=NOW).status == "CANCELLED"
    assert store.cancel(card.id, 17, -100, now=NOW).status == "CANCELLED"


@pytest.mark.parametrize(
    "overrides",
    [
        {"target": 1},
        {"target": 101},
        {"target": True},
        {"title": " "},
        {"title": "a" * 201},
        {"title": "hello\nworld"},
        {"title": "hello\x00world"},
        {"title": "hello\u202eworld"},
        {"deadline": NOW + 59},
        {"deadline": NOW + 604801},
    ],
)
def test_validation_rolls_back(store, overrides):
    with pytest.raises(DomainError):
        create(store, **overrides)
    assert store.health()["cards"] == 0


def test_active_limit_and_scope(store):
    for i in range(20):
        create(store, update_id=i)
    with pytest.raises(DomainError, match="limit"):
        create(store, update_id=21)
    create(store, update_id=22, chat_id=-200)
    assert len(store.active(-100, 1000)) == 20
    assert len(store.active(-200)) == 1


def test_dirty_flags_persistence_offsets_and_migration(tmp_path):
    path = str(tmp_path / "persistent.sqlite3")
    store = Store(path, SECRET)
    card = create(store)
    store.set_message(card.id, 500)
    store.set_offset(102)
    store.set_offset(90)
    store.close()
    store = Store(path, SECRET)
    assert store.get_offset() == 102
    assert store.dirty_cards()[0].message_id == 500
    store.mark_clean(card.id)
    assert store.dirty_cards() == []
    store.vote(card.id, 17, True, -100, now=NOW)
    assert len(store.dirty_cards()) == 1
    assert store.health()["database"] == "ok"
    store.close()


def test_forget_cross_card_erasure_and_final_aggregate(store):
    first = create(store)
    second = create(store, update_id=102, chat_id=-200)
    for card in (first, second):
        store.vote(card.id, 17, True, card.chat_id, now=NOW)
        store.vote(card.id, 18, True, card.chat_id, now=NOW)
    store.cancel(second.id, 17, -200, now=NOW)
    assert store.forget(17, now=NOW) == 2
    assert store.get(first.id).count == 1
    assert store.get(first.id).status == "OPEN"
    assert store.get(second.id).count == 2  # Closed-card historical aggregate.
    assert store.get(first.id).creator_key == ""
    assert store.get(second.id).creator_key == ""
    assert store.forget(17, now=NOW) == 0
    with pytest.raises(DomainError, match="creator"):
        store.cancel(first.id, 17, -100, now=NOW)


def test_purge_cascades_and_preserves_active(store):
    terminal = create(store)
    active = create(store, update_id=102, deadline=NOW + 700)
    store.vote(terminal.id, 17, True, -100, now=NOW)
    store.tick(now=NOW + 600)
    assert store.purge(NOW + 601) == 1
    assert store.get(terminal.id) is None
    assert store.get(active.id) is not None


def test_forget_after_deadline_preserves_result_without_scheduler(store):
    card = create(store)
    store.vote(card.id, 17, True, -100, now=NOW)
    store.vote(card.id, 18, True, -100, now=NOW)
    store.forget(17, now=card.deadline)
    assert store.get(card.id).status == "MET"
    assert store.get(card.id).count == 2


def test_no_raw_user_ids_stored_and_card_scoped_pseudonyms(tmp_path):
    path = str(tmp_path / "privacy.sqlite3")
    store = Store(path, SECRET)
    user_id = 73486745219
    first = create(store, user_id=user_id)
    second = create(store, update_id=102, user_id=user_id)
    store.vote(first.id, user_id, True, -100, now=NOW)
    assert first.creator_key != second.creator_key
    assert "creator_key" not in repr(first)
    conn = sqlite3.connect(path)
    dump = "\n".join(conn.iterdump())
    assert str(user_id) not in dump
    assert SECRET.decode() not in dump
    assert first.creator_key in dump
    conn.close()
    store.close()


def test_identity_is_hmac_sha256():
    # Independent standard-library HMAC vector, not an identity/security claim.
    import hashlib
    import hmac

    expected = hmac.new(SECRET, b"rallypoint:participant:v1:abc:17", hashlib.sha256).hexdigest()
    assert participant_key(SECRET, "abc", 17) == expected


def test_unknown_schema_and_short_secret_fail(tmp_path):
    path = str(tmp_path / "future.sqlite3")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version = 200")
    conn.close()
    with pytest.raises(RuntimeError, match="schema"):
        Store(path, SECRET)
    with pytest.raises(ValueError, match="32"):
        Store(":memory:", b"short")
