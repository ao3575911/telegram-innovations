"""SQLite persistence for one sequential bot worker.

Database mutations and the durable dirty-card flag commit together. Telegram
edits happen later and may safely be repeated. Sending a new Telegram message
cannot be exactly-once across a crash because Bot API has no idempotency key.
"""

import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path

from telegram_innovation.features.cards import Card, DomainError, validate_card
from telegram_innovation.security.identity import participant_key

CARD_FIELDS = (
    "id, chat_id, thread_id, message_id, title, target, deadline, status, count, creator_key"
)


class Store:
    """Synchronous, bounded SQLite operations; do not share across threads."""

    def __init__(self, path: str, secret: bytes) -> None:
        if len(secret) < 32:
            raise ValueError("The identity secret must contain at least 32 bytes.")
        self._secret = secret
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._db = sqlite3.connect(path, isolation_level=None, timeout=5)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA busy_timeout = 5000")
        self._db.execute("PRAGMA journal_mode = WAL")
        self._db.execute("PRAGMA synchronous = FULL")
        self._db.execute("PRAGMA secure_delete = ON")
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            sql = (
                files("telegram_innovation.storage")
                .joinpath("migrations/001_initial.sql")
                .read_text(encoding="utf-8")
            )
            self._db.executescript("BEGIN IMMEDIATE;\n" + sql + "\nCOMMIT;")
        elif version != 1:
            self._db.close()
            raise RuntimeError("Unsupported database schema version.")

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._db.rollback()
            raise
        else:
            self._db.commit()

    @staticmethod
    def _now(now: int | None) -> int:
        return int(time.time()) if now is None else now

    def get(self, card_id: str) -> Card | None:
        row = self._db.execute(
            f"SELECT {CARD_FIELDS} FROM cards WHERE id = ?", (card_id,)
        ).fetchone()
        return Card(**dict(row)) if row else None

    def _require(self, card_id: str, chat_id: int) -> Card:
        card = self.get(card_id)
        if card is None or card.chat_id != chat_id:
            raise DomainError("This card is unavailable in this chat.")
        return card

    def create(
        self,
        update_id: int,
        chat_id: int,
        user_id: int,
        title: str,
        target: int,
        deadline: int,
        thread_id: int | None = None,
        now: int | None = None,
    ) -> Card:
        instant = self._now(now)
        with self._transaction():
            existing = self._db.execute(
                "SELECT id FROM cards WHERE update_id = ?", (update_id,)
            ).fetchone()
            if existing:
                return self._require(existing["id"], chat_id)
            title = title.strip()
            validate_card(title, target, deadline, instant)
            active = self._db.execute(
                "SELECT count(*) FROM cards WHERE status IN ('OPEN','READY') AND chat_id = ?",
                (chat_id,),
            ).fetchone()[0]
            total = self._db.execute(
                "SELECT count(*) FROM cards WHERE status IN ('OPEN','READY')"
            ).fetchone()[0]
            if active >= 20 or total >= 10000:
                raise DomainError("The active-card limit has been reached. Try again later.")
            card_id = uuid.uuid4().hex
            key = participant_key(self._secret, card_id, user_id)
            self._db.execute(
                "INSERT INTO cards(id, update_id, chat_id, thread_id, title, target, "
                "deadline, status, creator_key) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)",
                (card_id, update_id, chat_id, thread_id, title, target, deadline, key),
            )
            return self._require(card_id, chat_id)

    def _recount(self, card_id: str) -> None:
        self._db.execute(
            "UPDATE cards SET count = (SELECT count(*) FROM votes WHERE card_id = ?), "
            "dirty = 1 WHERE id = ?",
            (card_id, card_id),
        )
        self._db.execute(
            "UPDATE cards SET status = CASE WHEN count >= target THEN 'READY' ELSE 'OPEN' END "
            "WHERE id = ? AND status IN ('OPEN','READY')",
            (card_id,),
        )

    def vote(
        self,
        card_id: str,
        user_id: int,
        join: bool,
        chat_id: int,
        now: int | None = None,
    ) -> Card:
        instant = self._now(now)
        with self._transaction():
            card = self._require(card_id, chat_id)
            if card.status not in ("OPEN", "READY") or card.deadline <= instant:
                raise DomainError("This card has closed. Commitments can no longer change.")
            key = participant_key(self._secret, card_id, user_id)
            if join:
                self._db.execute(
                    "INSERT OR IGNORE INTO votes(card_id, participant_key) VALUES (?, ?)",
                    (card_id, key),
                )
            else:
                self._db.execute(
                    "DELETE FROM votes WHERE card_id = ? AND participant_key = ?", (card_id, key)
                )
            self._recount(card_id)
            return self._require(card_id, chat_id)

    def cancel(
        self,
        card_id: str,
        user_id: int,
        chat_id: int,
        is_admin: bool = False,
        now: int | None = None,
    ) -> Card:
        instant = self._now(now)
        with self._transaction():
            card = self._require(card_id, chat_id)
            if not is_admin and card.creator_key != participant_key(self._secret, card_id, user_id):
                raise DomainError("Only the creator or a chat administrator can cancel this card.")
            if card.status == "CANCELLED":
                return card
            if card.status not in ("OPEN", "READY") or card.deadline <= instant:
                raise DomainError("This card has already closed.")
            self._db.execute(
                "UPDATE cards SET status = 'CANCELLED', dirty = 1 WHERE id = ?", (card_id,)
            )
            return self._require(card_id, chat_id)

    def set_message(self, card_id: str, message_id: int) -> None:
        self._db.execute("UPDATE cards SET message_id = ? WHERE id = ?", (message_id, card_id))

    def dirty_cards(self) -> list[Card]:
        rows = self._db.execute(
            f"SELECT {CARD_FIELDS} FROM cards WHERE dirty = 1 ORDER BY deadline LIMIT 100"
        ).fetchall()
        return [Card(**dict(row)) for row in rows]

    def mark_clean(self, card_id: str) -> None:
        self._db.execute("UPDATE cards SET dirty = 0 WHERE id = ?", (card_id,))

    def tick(self, now: int | None = None) -> list[Card]:
        instant = self._now(now)
        with self._transaction():
            rows = self._db.execute(
                "SELECT id FROM cards WHERE status IN ('OPEN','READY') AND deadline <= ?",
                (instant,),
            ).fetchall()
            self._db.execute(
                "UPDATE cards SET status = CASE WHEN count >= target THEN 'MET' ELSE 'MISSED' END, "
                "dirty = 1 WHERE status IN ('OPEN','READY') AND deadline <= ?",
                (instant,),
            )
            return [card for row in rows if (card := self.get(row["id"])) is not None]

    def forget(self, user_id: int, now: int | None = None) -> int:
        """Erase account links; final aggregates remain immutable historical counts.

        Active counts are recalculated. Titles are shared group content, so the
        command cannot erase names a creator chose to type into a card title.
        """
        affected = 0
        with self._transaction():
            # An overdue scheduler must not let erasure rewrite a closed result.
            self._db.execute(
                "UPDATE cards SET status = CASE WHEN count >= target THEN 'MET' ELSE 'MISSED' END, "
                "dirty = 1 WHERE status IN ('OPEN','READY') AND deadline <= ?",
                (self._now(now),),
            )
            rows = self._db.execute("SELECT id, creator_key, status FROM cards").fetchall()
            for row in rows:
                key = participant_key(self._secret, row["id"], user_id)
                removed = self._db.execute(
                    "DELETE FROM votes WHERE card_id = ? AND participant_key = ?", (row["id"], key)
                ).rowcount
                creator = row["creator_key"] == key
                if creator:
                    self._db.execute("UPDATE cards SET creator_key = '' WHERE id = ?", (row["id"],))
                if removed and row["status"] in ("OPEN", "READY"):
                    self._recount(row["id"])
                if removed or creator:
                    affected += 1
        return affected

    def purge(self, before: int) -> int:
        with self._transaction():
            return self._db.execute(
                "DELETE FROM cards WHERE status IN ('MET','MISSED','CANCELLED') AND deadline < ?",
                (before,),
            ).rowcount

    def active(self, chat_id: int, limit: int = 10) -> list[Card]:
        rows = self._db.execute(
            f"SELECT {CARD_FIELDS} FROM cards WHERE chat_id = ? AND status IN ('OPEN','READY') "
            "ORDER BY deadline LIMIT ?",
            (chat_id, min(max(limit, 1), 20)),
        ).fetchall()
        return [Card(**dict(row)) for row in rows]

    def health(self) -> dict[str, int | str]:
        integrity = self._db.execute("PRAGMA quick_check(1)").fetchone()[0]
        return {
            "database": "ok" if integrity == "ok" else "error",
            "cards": self._db.execute("SELECT count(*) FROM cards").fetchone()[0],
            "active": self._db.execute(
                "SELECT count(*) FROM cards WHERE status IN ('OPEN','READY')"
            ).fetchone()[0],
            "pending": self._db.execute("SELECT count(*) FROM cards WHERE dirty = 1").fetchone()[0],
        }

    def get_offset(self) -> int:
        return int(
            self._db.execute("SELECT value FROM metadata WHERE key = 'offset'").fetchone()[0]
        )

    def set_offset(self, offset: int) -> None:
        self._db.execute(
            "UPDATE metadata SET value = max(value, ?) WHERE key = 'offset'", (offset,)
        )

    def close(self) -> None:
        self._db.close()
