CREATE TABLE cards (
    id TEXT PRIMARY KEY,
    update_id INTEGER NOT NULL UNIQUE,
    chat_id INTEGER NOT NULL,
    thread_id INTEGER,
    message_id INTEGER,
    title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 200),
    target INTEGER NOT NULL CHECK(target BETWEEN 2 AND 100),
    deadline INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('OPEN','READY','MET','MISSED','CANCELLED')),
    count INTEGER NOT NULL DEFAULT 0 CHECK(count >= 0),
    creator_key TEXT NOT NULL,
    dirty INTEGER NOT NULL DEFAULT 1 CHECK(dirty IN (0,1))
);
CREATE TABLE votes (
    card_id TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    participant_key TEXT NOT NULL,
    PRIMARY KEY(card_id, participant_key)
);
CREATE INDEX cards_deadline ON cards(status, deadline);
CREATE INDEX cards_chat ON cards(chat_id, status);
CREATE TABLE metadata (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
INSERT INTO metadata(key, value) VALUES ('offset', 0);
PRAGMA user_version = 1;
