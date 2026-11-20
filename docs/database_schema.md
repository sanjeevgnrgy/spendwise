# Database Schema

SpendWise keeps everything in one database: a SQLite file, `backend/spendwise.db`, by default (`DATABASE_URL` can
point elsewhere, e.g. Postgres). Each table belongs to **exactly one module**, and only that module reads or writes it.

## Tables at a glance

```mermaid
erDiagram
    category {
        INTEGER id PK
        VARCHAR_50 name "unique, any letter case"
        VARCHAR_50 icon
    }
    expense {
        INTEGER id PK
        INTEGER owner_id "the person; indexed with spent_on"
        INTEGER amount_minor "paise"
        VARCHAR_3 currency
        INTEGER category_id "indexed, no foreign key"
        VARCHAR_100 merchant
        VARCHAR_500 note "nullable"
        DATE spent_on "indexed"
        VARCHAR_20 payment_method
        DATETIME created_at "UTC, with time zone"
        INTEGER version "starts at 1"
        INTEGER base_amount_minor "INR paise, nullable"
        VARCHAR_32 exchange_rate "nullable"
        DATE rate_date "nullable"
    }
    conversation_message {
        INTEGER id PK
        INTEGER owner_id "the person; indexed with thread_id, turn"
        VARCHAR_32 thread_id
        INTEGER turn
        VARCHAR_30 kind
        JSON content "a provider-neutral message"
        DATETIME created_at
    }
    pending_approval {
        VARCHAR_64 approval_id PK "the card's surface id"
        INTEGER owner_id "the person; indexed"
        VARCHAR_32 thread_id "indexed"
        JSON expense "snapshot shown on the card"
        DATETIME created_at "indexed"
    }
    receipt_file {
        INTEGER id PK
        INTEGER owner_id "the person; indexed"
        VARCHAR_32 storage_key "unique; the file is in UPLOADS_DIR"
        VARCHAR_15 media_type "read from the file's bytes"
        INTEGER size_bytes
        DATETIME created_at "UTC, with time zone"
    }
    app_user {
        INTEGER id PK "SpendWise's own id for a person"
        VARCHAR_200 name "as the provider last said"
        VARCHAR_320 email
        BOOLEAN email_verified
        VARCHAR_2048 avatar_url "http(s) only"
        BOOLEAN is_active
        DATETIME created_at
        DATETIME updated_at
    }
    user_identity {
        INTEGER id PK
        INTEGER user_id FK "indexed"
        VARCHAR_255 issuer "unique with subject"
        VARCHAR_255 subject
        VARCHAR_320 email "when first seen"
        DATETIME created_at
    }
    user_session {
        INTEGER id PK
        VARCHAR_64 key_hash "unique; SHA-256 of the cookie's key"
        VARCHAR_32 handle "unique; the sign-out link's sid"
        INTEGER user_id FK "indexed"
        VARCHAR_255 issuer
        VARCHAR_255 provider_session_id "indexed; OIDC sid"
        TEXT sealed_id_token "encrypted"
        DATETIME created_at
        DATETIME renewed_at
        DATETIME expires_at "indexed; idle"
        DATETIME absolute_expires_at
        DATETIME revoked_at "nullable"
        VARCHAR_255 user_agent "nullable"
    }
    login_attempt {
        INTEGER id PK
        VARCHAR_64 key_hash "unique"
        VARCHAR_64 state
        VARCHAR_64 nonce
        VARCHAR_128 code_verifier
        VARCHAR_2048 return_to
        DATETIME created_at "indexed"
    }
    access_token {
        INTEGER id PK
        INTEGER user_id FK "indexed"
        VARCHAR_50 name
        VARCHAR_64 token_hash "unique; SHA-256 of the token"
        VARCHAR_4 hint "its last characters"
        DATETIME created_at
        DATETIME expires_at
        DATETIME last_used_at "nullable"
    }
    category ||..o{ expense : "category_id (checked in code)"
    app_user ||--o{ user_identity : "user_id"
    app_user ||--o{ user_session : "user_id"
    app_user ||--o{ access_token : "user_id"
```

The dotted line is a link kept **in code**, not by the database: there are no foreign keys between modules (below).
`pending_approval.thread_id` and `conversation_message.thread_id` name the same conversations, also without a key.

| Table | Owner module | Holds |
|---|---|---|
| `category` | categories | the spending categories |
| `expense` | expenses | every expense |
| `conversation_message` | conversations | chat history, one row per message |
| `pending_approval` | assistant | delete cards waiting for Approve or Cancel |
| `receipt_file` | receipts | uploaded receipts (the files themselves are in `UPLOADS_DIR`, not the database) |
| `app_user` | accounts | the people who use SpendWise, by SpendWise's own id |
| `user_identity` | accounts | how each person signs in: a provider (issuer) and their id there (subject) |
| `user_session` | accounts | signed-in browsers: the hash of each cookie's key, and the session's lifetimes |
| `login_attempt` | accounts | sign-ins that have left for the provider and not come back yet |
| `access_token` | accounts | personal access tokens for MCP clients: the hash of each, never the token |
| `alembic_version` | (migrations) | which migration the database is at |

## `category`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER, primary key | |
| `name` | VARCHAR(50), not null | unique index `ix_category_name`; the app also refuses names that differ only in letter case ("food" vs "Food") |
| `icon` | VARCHAR(50), not null | an icon *name* (`utensils`), mapped to a picture by the web app |

## `expense`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER, primary key | shown everywhere as `#14` |
| `owner_id` | INTEGER, not null | whose expense it is (SpendWise's user id, no foreign key: D13). Every read and change filters on it (D190); the index `ix_expense_owner_id_spent_on` (owner_id, spent_on) serves "my expenses this month" |
| `amount_minor` | INTEGER, not null | **whole paise**: ₹450.50 is `45050`. Never a float |
| `currency` | VARCHAR(3), not null | ISO 4217 code, default `INR` |
| `category_id` | INTEGER, not null | index `ix_expense_category_id`. **No foreign key**: the expenses module asks the categories module whether the category exists |
| `merchant` | VARCHAR(100), not null | trimmed of spaces |
| `note` | VARCHAR(500), nullable | |
| `spent_on` | DATE, not null | second column of `ix_expense_owner_id_spent_on` |
| `payment_method` | VARCHAR(20), not null | `cash`, `upi`, `card`, `netbanking`, `wallet` or `other` |
| `created_at` | DATETIME with time zone, not null | UTC, set from the app's clock |
| `version` | INTEGER, not null, default 1 | raised by one on every update: **optimistic concurrency** |
| `base_amount_minor` | INTEGER, nullable | the same amount in INR, whole paise (D204): what totals add up. Equal to `amount_minor` for INR |
| `exchange_rate` | VARCHAR(32), nullable | the rate it was converted at, exactly, as text (`"84.5"`; `"1"` for INR) |
| `rate_date` | DATE, nullable | the day the rate is for (the expense's date, or the nearest earlier day the rates have) |

The three are null only for an expense in another currency saved before migration 0008: it's left out of totals
until a new amount, currency or date converts it.

### Why `version`

The assistant's Approve card shows an expense and later deletes it. If the expense was edited in between (from the
table, another tab, an MCP client), deleting it would remove something the user never saw. So the delete is one
statement:

```sql
DELETE FROM expense WHERE id = :id AND owner_id = :owner AND version = :version_on_the_card
```

If it deletes nothing, the expense changed (or is gone), and the user is told so. No lock is held while waiting for
the user, and nothing can slip in between the check and the delete.

## `conversation_message`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER, primary key | also the order of messages |
| `owner_id` | INTEGER, not null | whose conversation it is. A thread is (owner_id, thread_id): the same id from two people is two conversations (D190) |
| `thread_id` | VARCHAR(32), not null | with `owner_id` and `turn`, the index `ix_conversation_message_owner_id_thread_id_turn`: every read of a thread filters on all three |
| `turn` | INTEGER, not null | 1 for the first user message of a thread, 2 for the next, … Only the last 10 turns are resent to the model |
| `kind` | VARCHAR(30), not null | `user_text`, `assistant_text`, `tool_call`, `tool_result` or `reasoning` (also inside `content`) |
| `content` | JSON, not null | the message, in SpendWise's own format, not any provider's |
| `created_at` | DATETIME with time zone, not null | |

What `content` looks like for each kind:

```json
{"kind": "user_text", "text": "Add 250 for lunch at Subway"}
{"kind": "assistant_text", "text": "Saved ₹250 at Subway."}
{"kind": "tool_call", "call_id": "c1", "name": "add_expense", "arguments": {"amount": "250", "merchant": "Subway"}}
{"kind": "tool_result", "call_id": "c1", "name": "add_expense", "output": "{…}", "is_error": false}
{"kind": "reasoning", "provider": "gemini", "opaque": {"signature": "c2ln…"}}
```

A turn is written in one transaction once it has finished, so a thread never holds half a turn. `reasoning` keeps a
provider's private data (Gemini's thought signature, needed to continue after a tool call) for that provider only.

## `pending_approval`

| Column | Type | Notes |
|---|---|---|
| `approval_id` | VARCHAR(64), primary key | the Approve/Cancel card's surface id, what the browser sends back |
| `owner_id` | INTEGER, not null | index; only the card's owner can answer it |
| `thread_id` | VARCHAR(32), not null | index; a card can only be answered in its own conversation |
| `expense` | JSON, not null | the expense exactly as the card showed it, including its `version` |
| `created_at` | DATETIME with time zone, not null | index; cards expire after 15 minutes |

At most 200 are kept per person (their oldest forgotten first). Taking a card removes it, so each card decides once; if the decision
fails midway, the card is put back unchanged (same age).

## `receipt_file`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER, primary key | the receipt's id (`POST /receipts` answers it) |
| `owner_id` | INTEGER, not null | index; who uploaded it: only they can see it, have it read or attach it |
| `storage_key` | VARCHAR(32), unique, not null | where the bytes are: a random key (a UUID's hex digits) the `FileStore` made, never a name the user sent |
| `media_type` | VARCHAR(15), not null | `image/jpeg`, `image/png`, `image/webp` or `application/pdf`, read from the file's first bytes |
| `size_bytes` | INTEGER, not null | at most 5 MB |
| `created_at` | DATETIME with time zone, not null | when it was uploaded (UTC) |

**The bytes aren't in the database.** A receipt can be megabytes; the database keeps the row, and the file is kept in
`UPLOADS_DIR` under its key (D181). The upload saves the file first and deletes it again if the row can't be added,
so there's never a file without a row. Nothing deletes receipts yet.

## The accounts tables

Owned by the accounts module (Phase 22, D186, D187). The solid lines are real foreign keys: they stay inside the
module, which D13 allows (it forbids them between modules).

### `app_user`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER, primary key | SpendWise's own id for the person: what every other module's `owner_id` points at (D190), whatever provider they use |
| `name`, `email`, `email_verified`, `avatar_url` | VARCHAR(200), VARCHAR(320), BOOLEAN, VARCHAR(2048) | the profile as the provider said at the last sign-in; never used to find a person. A picture is kept only as an http(s) URL |
| `is_active` | BOOLEAN, not null | SpendWise's own off switch: off, the person can't sign in and their sessions stop working |
| `created_at`, `updated_at` | DATETIME with time zone | UTC, from the app's clock |

### `user_identity`

| Column | Type | Notes |
|---|---|---|
| `user_id` | INTEGER, foreign key to `app_user.id` | indexed |
| `issuer`, `subject` | VARCHAR(255) each | **unique together**: the provider and the person's id there. How a person is found at sign-in; never by email (D187) |
| `email` | VARCHAR(320), nullable | the email when this identity was first seen, as a record |

A person can have several identities: that's how a later switch of provider can keep them the same person
([identity_provider.md](identity_provider.md#switching-providers)).

### `user_session`

| Column | Type | Notes |
|---|---|---|
| `key_hash` | VARCHAR(64), unique | SHA-256 of the cookie's random key; the key itself is never stored |
| `handle` | VARCHAR(32), unique | a random public name for the session; the sign-out link carries it |
| `user_id` | INTEGER, foreign key to `app_user.id` | indexed |
| `issuer` | VARCHAR(255) | the provider it was signed in with; a session from another provider isn't accepted |
| `provider_session_id` | VARCHAR(255), nullable, indexed | the provider's session (OIDC `sid`), for back-channel logout |
| `sealed_id_token` | TEXT, nullable | the ID token, encrypted with `SESSION_ENCRYPTION_KEYS` (Fernet); signing out names it to the provider |
| `renewed_at`, `expires_at` | DATETIME | renewed while used (written at most every 12 h); `expires_at` (indexed) is a day after the last renewal |
| `absolute_expires_at` | DATETIME | 14 days after sign-in, whatever happens |
| `revoked_at` | DATETIME, nullable | set by signing out, a new sign-in in the same browser, the provider's back-channel logout, or signing it out from Settings |
| `user_agent` | VARCHAR(255), nullable | the browser's User-Agent at sign-in, so the person can tell their sessions apart; shown only to them |

A session is live when it isn't revoked, both expiries are in the future, its issuer is today's provider's, and its
user is active: all checked in one query. Ended sessions are deleted at the next sign-in.

### `login_attempt`

| Column | Type | Notes |
|---|---|---|
| `key_hash` | VARCHAR(64), unique | SHA-256 of the login cookie's key: the attempt completes only in the browser that started it |
| `state`, `nonce`, `code_verifier` | VARCHAR(64), VARCHAR(64), VARCHAR(128) | what the callback checks the provider's answer against |
| `return_to` | VARCHAR(2048) | the web app's page to come back to, already checked |
| `created_at` | DATETIME, indexed | attempts over 10 minutes old are forgotten; at most 500 are kept |

Each attempt is read and deleted in one step when the provider sends the browser back, so it completes once.

### `access_token`

| Column | Type | Notes |
|---|---|---|
| `user_id` | INTEGER, foreign key to `app_user.id` | indexed; whose token it is |
| `name` | VARCHAR(50) | what its owner called it |
| `token_hash` | VARCHAR(64), unique | SHA-256 of the token; the token itself is shown once and never stored (D191) |
| `hint` | VARCHAR(4) | its last characters, shown in Settings |
| `created_at`, `expires_at` | DATETIME | it stops working at `expires_at`; revoking deletes the row |
| `last_used_at` | DATETIME, nullable | written at most once an hour |

## Rules every table follows

- **One owner.** Only the owning module's handlers touch a table. Other modules ask through the bus
  (`categories.GetCategory`), never with SQL.
- **No foreign keys between modules.** A foreign key would tie two modules together in the database. The trade-off:
  the database doesn't guard the link, so the owning module's command checks it (`CreateExpense` asks whether the
  category exists), and readers handle a missing one (`"Unknown"`).
- **Transactions come from the bus.** Handlers never commit; the bus commits once per command and rolls back on error.
  Repositories only stage changes.
- **Money in paise, time in UTC.** Integers for money, `Decimal` for conversions; timestamps stored with their time
  zone, converted for display by the web app.

## Migrations

The tables are created and changed only by **Alembic migrations** in `backend/migrations/versions/`:

| Revision | What it does |
|---|---|
| `0001_baseline` | the schema from Phases 3–18 (`category`, `expense`, `chatmessage`), each table created only if missing, so databases from before migrations keep their data |
| `0002_neutral_conversations` | renames `chatmessage` → `conversation_message` and converts every stored message from Gemini's format to SpendWise's own (and back, on downgrade); adds `pending_approval` |
| `0003_expense_version` | adds `expense.version` (existing expenses start at 1) |
| `0004_conversation_turn_index` | indexes `conversation_message` on (thread_id, turn) and drops the old thread_id index, which the new one makes redundant |
| `0005_receipt_files` | adds `receipt_file` (Phase 21); downgrade drops it and leaves the files in `UPLOADS_DIR` |
| `0006_accounts` | adds `app_user`, `user_identity`, `user_session` and `login_attempt` (Phase 22); downgrade drops them, which signs everyone out and forgets them |
| `0007_owners` | **deletes the expenses, conversations, delete cards and receipt rows made before sign-in** (they belonged to nobody), then adds `owner_id` to those four tables with their new indexes, `access_token`, and `user_session.user_agent` (Phase 23). The receipt files stay in `UPLOADS_DIR`. Downgrade removes the additions; the deleted rows don't come back |
| `0008_base_amounts` | adds `expense.base_amount_minor`, `exchange_rate` and `rate_date` (Phase 25), filled in for expenses already in INR (their own amount, rate `1`, their own date); expenses in other currencies stay null (a migration can't call the currency agent). Downgrade drops the three columns |

- `.\run.ps1` runs `alembic upgrade head` before starting; `seed.py` and `mcp_stdio.py` do too. The app itself only
  checks, and refuses to start on an out-of-date database with the command to fix it.
- An `upgrade` runs in **one transaction**, schema changes included (SQLite is set up for this in
  `infrastructure/db.py`): if any step fails, the database is left exactly as it was.
- Migrations don't import app code: a migration must keep doing exactly what it did after the code changes.
- SQLite can't alter most of a table in place, so changes run in Alembic's **batch mode** (copy into a new table).

Commands (from the project folder):

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini current                  # where the database is
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head             # bring it up to date
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini downgrade -1             # undo the last one
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini revision --autogenerate -m "what changed"
```

Read every generated migration before running it: autogenerate is a draft, not a decision.

## Moving to Postgres later

Set `DATABASE_URL=postgresql+psycopg://…` and run the migrations. What already fits: timestamps with time zone,
`EXTRACT(year/month …)` in the trend query (standard SQL, not SQLite's `strftime`), JSON columns, batch mode (a no-op
outside SQLite). What to revisit then: the SQLite-specific connection settings in `infrastructure/db.py` (they apply
only to SQLite), and indexes for the JSON columns if they're ever queried.
