DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS polls;
DROP TABLE IF EXISTS choices;
DROP TABLE IF EXISTS ballots;
DROP TABLE IF EXISTS voters;
DROP TABLE IF EXISTS tokens;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subject TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT "Einfach",
    state TEXT NOT NULL DEFAULT "Vorbereitet",
    FOREIGN KEY (author_id) REFERENCES users (id),
    CONSTRAINT type_choices CHECK (type IN ("Einfach", "Namentlich", "Gewichtet", "Geheim")),
    CONSTRAINT state_choices CHECK (state IN ("Vorbereitet", "Offen", "Geschlossen", "Gelöscht"))
);

CREATE TABLE choices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (poll_id) REFERENCES polls (id)
);

CREATE TABLE ballots (
    choice_id INTEGER NOT NULL,
    voter_id INTEGER NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (choice_id) REFERENCES choices (id),
    FOREIGN KEY (voter_id) REFERENCES tokens (id),
    CONSTRAINT unique_ballot UNIQUE (choice_id, voter_id)
);

CREATE TABLE voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    weight INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE tokens (
    voter_id INTEGER NOT NULL,
    key TEXT PRIMARY KEY,
    expired BOOLEAN NOT NULL DEFAULT FALSE,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (voter_id) REFERENCES voters (id)
);
