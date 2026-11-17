"""
database.py
SQLite persistence layer for Campfire Studio Clone.

Provides a multi-project schema where every worldbuilding record
(characters, attributes, languages, grammar rules, lexicon entries,
locations, events, manuscripts, magic systems, religions) is isolated
per-project via foreign keys with cascading deletes.
"""

import datetime
import os
import sqlite3
import sys

DB_FILENAME = "story_forge.db"

class Database:
    """Thin, explicit wrapper around sqlite3 for the application."""
    def __init__(self, db_path=None):
        if db_path is None:
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller EXE — use persistent AppData folder
                base_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), "StoryForge")
            else:
                # Running as normal script
                base_dir = os.path.dirname(os.path.abspath(__file__))
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, DB_FILENAME)
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._create_schema()
    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _create_schema(self):
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                font_path   TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS characters (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                name        TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT '',
                bio         TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS character_attributes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id  INTEGER NOT NULL,
                attr_key      TEXT NOT NULL,
                attr_value    TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (character_id) REFERENCES characters (id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS languages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                name        TEXT NOT NULL,
                grammar     TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS lexicon_entries (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                language_id    INTEGER NOT NULL,
                word           TEXT NOT NULL,
                translation    TEXT NOT NULL DEFAULT '',
                part_of_speech TEXT NOT NULL DEFAULT '',
                notes          TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (language_id) REFERENCES languages (id)
                    ON DELETE CASCADE
            );

            -- -------------------------------------------------------
            -- Locations
            -- -------------------------------------------------------
            CREATE TABLE IF NOT EXISTS locations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                climate     TEXT NOT NULL DEFAULT '',
                population  TEXT NOT NULL DEFAULT '',
                notes       TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS location_attributes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id INTEGER NOT NULL,
                attr_key    TEXT NOT NULL,
                attr_value  TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (location_id) REFERENCES locations (id)
                    ON DELETE CASCADE
            );

            -- -------------------------------------------------------
            -- Events
            -- -------------------------------------------------------
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                title       TEXT NOT NULL,
                event_type  TEXT NOT NULL DEFAULT '',
                date_label  TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                location_id INTEGER,
                notes       TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
                    ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES locations (id)
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS event_characters (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id     INTEGER NOT NULL,
                character_id INTEGER NOT NULL,
                FOREIGN KEY (event_id)     REFERENCES events (id)     ON DELETE CASCADE,
                FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
            );

            -- -------------------------------------------------------
            -- Manuscripts
            -- -------------------------------------------------------
            CREATE TABLE IF NOT EXISTS manuscripts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                title       TEXT NOT NULL,
                genre       TEXT NOT NULL DEFAULT '',
                synopsis    TEXT NOT NULL DEFAULT '',
                status      TEXT NOT NULL DEFAULT 'Draft',
                word_count  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS manuscript_chapters (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                manuscript_id   INTEGER NOT NULL,
                chapter_number  INTEGER NOT NULL DEFAULT 1,
                title           TEXT NOT NULL DEFAULT '',
                body            TEXT NOT NULL DEFAULT '',
                notes           TEXT NOT NULL DEFAULT '',
                status          TEXT NOT NULL DEFAULT 'Draft',
                FOREIGN KEY (manuscript_id) REFERENCES manuscripts (id)
                    ON DELETE CASCADE
            );

            -- -------------------------------------------------------
            -- Magic Systems
            -- -------------------------------------------------------
            CREATE TABLE IF NOT EXISTS magic_systems (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL,
                name            TEXT NOT NULL,
                classification  TEXT NOT NULL DEFAULT '',
                description     TEXT NOT NULL DEFAULT '',
                rules           TEXT NOT NULL DEFAULT '',
                source          TEXT NOT NULL DEFAULT '',
                limitations     TEXT NOT NULL DEFAULT '',
                cost            TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS magic_abilities (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                magic_system_id INTEGER NOT NULL,
                name            TEXT NOT NULL,
                description     TEXT NOT NULL DEFAULT '',
                tier            TEXT NOT NULL DEFAULT '',
                notes           TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (magic_system_id) REFERENCES magic_systems (id)
                    ON DELETE CASCADE
            );

            -- -------------------------------------------------------
            -- Timeline
            -- -------------------------------------------------------
            CREATE TABLE IF NOT EXISTS timeline_eras (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                name        TEXT NOT NULL,
                start_label TEXT NOT NULL DEFAULT '',
                end_label   TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                sort_order  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
                    ON DELETE CASCADE
            );

            -- -------------------------------------------------------
            -- Creatures
            -- -------------------------------------------------------
            CREATE TABLE IF NOT EXISTS creatures (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL,
                name            TEXT NOT NULL,
                creature_type   TEXT NOT NULL DEFAULT '',
                habitat         TEXT NOT NULL DEFAULT '',
                size            TEXT NOT NULL DEFAULT '',
                diet            TEXT NOT NULL DEFAULT '',
                behaviour       TEXT NOT NULL DEFAULT '',
                abilities       TEXT NOT NULL DEFAULT '',
                weaknesses      TEXT NOT NULL DEFAULT '',
                lore            TEXT NOT NULL DEFAULT '',
                notes           TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
                    ON DELETE CASCADE
            );

            -- -------------------------------------------------------
            -- Religions
            -- -------------------------------------------------------
            CREATE TABLE IF NOT EXISTS religions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL,
                name            TEXT NOT NULL,
                pantheon_type   TEXT NOT NULL DEFAULT '',
                description     TEXT NOT NULL DEFAULT '',
                beliefs         TEXT NOT NULL DEFAULT '',
                practices       TEXT NOT NULL DEFAULT '',
                holy_texts      TEXT NOT NULL DEFAULT '',
                afterlife_views TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS religion_deities (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                religion_id INTEGER NOT NULL,
                name        TEXT NOT NULL,
                domain      TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                alignment   TEXT NOT NULL DEFAULT '',
                notes       TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (religion_id) REFERENCES religions (id)
                    ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    @staticmethod
    def _now():
        return datetime.datetime.now().isoformat(timespec="seconds")

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def create_project(self, name, description=""):
        cur = self.conn.execute(
            "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?)",
            (name.strip(), description.strip(), self._now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_projects(self):
        cur = self.conn.execute("SELECT * FROM projects ORDER BY name COLLATE NOCASE")
        return [dict(row) for row in cur.fetchall()]

    def get_project(self, project_id):
        cur = self.conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def delete_project(self, project_id):
        self.conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()

    def set_project_font(self, project_id, font_path):
        self.conn.execute(
            "UPDATE projects SET font_path = ? WHERE id = ?", (font_path, project_id)
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Characters
    # ------------------------------------------------------------------
    def create_character(self, project_id, name, role="", bio=""):
        cur = self.conn.execute(
            "INSERT INTO characters (project_id, name, role, bio, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, name.strip(), role.strip(), bio, self._now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_character(self, character_id, name, role, bio):
        self.conn.execute(
            "UPDATE characters SET name = ?, role = ?, bio = ? WHERE id = ?",
            (name.strip(), role.strip(), bio, character_id),
        )
        self.conn.commit()

    def delete_character(self, character_id):
        self.conn.execute("DELETE FROM characters WHERE id = ?", (character_id,))
        self.conn.commit()

    def list_characters(self, project_id):
        cur = self.conn.execute(
            "SELECT * FROM characters WHERE project_id = ? ORDER BY name COLLATE NOCASE",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_character(self, character_id):
        cur = self.conn.execute(
            "SELECT * FROM characters WHERE id = ?", (character_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def set_character_attributes(self, character_id, pairs):
        """Replace all custom metadata attributes for a character.

        ``pairs`` is an iterable of (key, value) tuples.
        """
        self.conn.execute(
            "DELETE FROM character_attributes WHERE character_id = ?", (character_id,)
        )
        for key, value in pairs:
            key = key.strip()
            if not key:
                continue
            self.conn.execute(
                "INSERT INTO character_attributes (character_id, attr_key, attr_value) "
                "VALUES (?, ?, ?)",
                (character_id, key, value.strip()),
            )
        self.conn.commit()

    def get_character_attributes(self, character_id):
        cur = self.conn.execute(
            "SELECT attr_key, attr_value FROM character_attributes "
            "WHERE character_id = ? ORDER BY id",
            (character_id,),
        )
        return [(row["attr_key"], row["attr_value"]) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Languages
    # ------------------------------------------------------------------
    def create_language(self, project_id, name, grammar=""):
        cur = self.conn.execute(
            "INSERT INTO languages (project_id, name, grammar, created_at) "
            "VALUES (?, ?, ?, ?)",
            (project_id, name.strip(), grammar, self._now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_language(self, language_id, name, grammar):
        self.conn.execute(
            "UPDATE languages SET name = ?, grammar = ? WHERE id = ?",
            (name.strip(), grammar, language_id),
        )
        self.conn.commit()

    def delete_language(self, language_id):
        self.conn.execute("DELETE FROM languages WHERE id = ?", (language_id,))
        self.conn.commit()

    def list_languages(self, project_id):
        cur = self.conn.execute(
            "SELECT * FROM languages WHERE project_id = ? ORDER BY name COLLATE NOCASE",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_language(self, language_id):
        cur = self.conn.execute("SELECT * FROM languages WHERE id = ?", (language_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Lexicon
    # ------------------------------------------------------------------
    def replace_lexicon(self, language_id, entries):
        """Replace the full lexicon for a language.

        ``entries`` is an iterable of (word, translation, part_of_speech, notes).
        """
        self.conn.execute(
            "DELETE FROM lexicon_entries WHERE language_id = ?", (language_id,)
        )
        for word, translation, pos, notes in entries:
            word = word.strip()
            if not word:
                continue
            self.conn.execute(
                "INSERT INTO lexicon_entries "
                "(language_id, word, translation, part_of_speech, notes) "
                "VALUES (?, ?, ?, ?, ?)",
                (language_id, word, translation.strip(), pos.strip(), notes.strip()),
            )
        self.conn.commit()

    def list_lexicon(self, language_id):
        cur = self.conn.execute(
            "SELECT * FROM lexicon_entries WHERE language_id = ? "
            "ORDER BY word COLLATE NOCASE",
            (language_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------
    def create_location(self, project_id, name, loc_type="", description="",
                        climate="", population="", notes=""):
        cur = self.conn.execute(
            "INSERT INTO locations "
            "(project_id, name, type, description, climate, population, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, name.strip(), loc_type.strip(), description,
             climate.strip(), population.strip(), notes, self._now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_location(self, location_id, name, loc_type, description,
                        climate, population, notes):
        self.conn.execute(
            "UPDATE locations SET name=?, type=?, description=?, "
            "climate=?, population=?, notes=? WHERE id=?",
            (name.strip(), loc_type.strip(), description,
             climate.strip(), population.strip(), notes, location_id),
        )
        self.conn.commit()

    def delete_location(self, location_id):
        self.conn.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        self.conn.commit()

    def list_locations(self, project_id):
        cur = self.conn.execute(
            "SELECT * FROM locations WHERE project_id = ? ORDER BY name COLLATE NOCASE",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_location(self, location_id):
        cur = self.conn.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def set_location_attributes(self, location_id, pairs):
        """Replace all custom attributes for a location."""
        self.conn.execute(
            "DELETE FROM location_attributes WHERE location_id = ?", (location_id,)
        )
        for key, value in pairs:
            key = key.strip()
            if not key:
                continue
            self.conn.execute(
                "INSERT INTO location_attributes (location_id, attr_key, attr_value) "
                "VALUES (?, ?, ?)",
                (location_id, key, value.strip()),
            )
        self.conn.commit()

    def get_location_attributes(self, location_id):
        cur = self.conn.execute(
            "SELECT attr_key, attr_value FROM location_attributes "
            "WHERE location_id = ? ORDER BY id",
            (location_id,),
        )
        return [(row["attr_key"], row["attr_value"]) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def create_event(self, project_id, title, event_type="", date_label="",
                     description="", location_id=None, notes=""):
        cur = self.conn.execute(
            "INSERT INTO events "
            "(project_id, title, event_type, date_label, description, location_id, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, title.strip(), event_type.strip(), date_label.strip(),
             description, location_id, notes, self._now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_event(self, event_id, title, event_type, date_label,
                     description, location_id, notes):
        self.conn.execute(
            "UPDATE events SET title=?, event_type=?, date_label=?, "
            "description=?, location_id=?, notes=? WHERE id=?",
            (title.strip(), event_type.strip(), date_label.strip(),
             description, location_id, notes, event_id),
        )
        self.conn.commit()

    def delete_event(self, event_id):
        self.conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        self.conn.commit()

    def list_events(self, project_id):
        cur = self.conn.execute(
            "SELECT * FROM events WHERE project_id = ? ORDER BY date_label COLLATE NOCASE",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_event(self, event_id):
        cur = self.conn.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def set_event_characters(self, event_id, character_ids):
        """Replace the character list linked to an event."""
        self.conn.execute("DELETE FROM event_characters WHERE event_id = ?", (event_id,))
        for cid in character_ids:
            self.conn.execute(
                "INSERT INTO event_characters (event_id, character_id) VALUES (?, ?)",
                (event_id, cid),
            )
        self.conn.commit()

    def get_event_characters(self, event_id):
        cur = self.conn.execute(
            "SELECT c.* FROM characters c "
            "JOIN event_characters ec ON ec.character_id = c.id "
            "WHERE ec.event_id = ? ORDER BY c.name COLLATE NOCASE",
            (event_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Manuscripts
    # ------------------------------------------------------------------
    def create_manuscript(self, project_id, title, genre="", synopsis="",
                          status="Draft"):
        now = self._now()
        cur = self.conn.execute(
            "INSERT INTO manuscripts "
            "(project_id, title, genre, synopsis, status, word_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
            (project_id, title.strip(), genre.strip(), synopsis, status, now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_manuscript(self, manuscript_id, title, genre, synopsis, status):
        self.conn.execute(
            "UPDATE manuscripts SET title=?, genre=?, synopsis=?, status=?, updated_at=? "
            "WHERE id=?",
            (title.strip(), genre.strip(), synopsis, status, self._now(), manuscript_id),
        )
        self.conn.commit()

    def delete_manuscript(self, manuscript_id):
        self.conn.execute("DELETE FROM manuscripts WHERE id = ?", (manuscript_id,))
        self.conn.commit()

    def list_manuscripts(self, project_id):
        cur = self.conn.execute(
            "SELECT * FROM manuscripts WHERE project_id = ? ORDER BY title COLLATE NOCASE",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_manuscript(self, manuscript_id):
        cur = self.conn.execute(
            "SELECT * FROM manuscripts WHERE id = ?", (manuscript_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def _recalc_word_count(self, manuscript_id):
        """Recount total words across all chapters and persist."""
        cur = self.conn.execute(
            "SELECT body FROM manuscript_chapters WHERE manuscript_id = ?",
            (manuscript_id,),
        )
        total = sum(len(row["body"].split()) for row in cur.fetchall())
        self.conn.execute(
            "UPDATE manuscripts SET word_count=?, updated_at=? WHERE id=?",
            (total, self._now(), manuscript_id),
        )
        self.conn.commit()

    # Chapters ----
    def add_chapter(self, manuscript_id, title="", body="", notes="",
                    status="Draft"):
        cur = self.conn.execute(
            "SELECT COALESCE(MAX(chapter_number), 0) + 1 AS next_num "
            "FROM manuscript_chapters WHERE manuscript_id = ?",
            (manuscript_id,),
        )
        next_num = cur.fetchone()["next_num"]
        cur = self.conn.execute(
            "INSERT INTO manuscript_chapters "
            "(manuscript_id, chapter_number, title, body, notes, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (manuscript_id, next_num, title.strip(), body, notes, status),
        )
        self.conn.commit()
        self._recalc_word_count(manuscript_id)
        return cur.lastrowid

    def update_chapter(self, chapter_id, title, body, notes, status):
        cur = self.conn.execute(
            "SELECT manuscript_id FROM manuscript_chapters WHERE id = ?", (chapter_id,)
        )
        row = cur.fetchone()
        self.conn.execute(
            "UPDATE manuscript_chapters SET title=?, body=?, notes=?, status=? WHERE id=?",
            (title.strip(), body, notes, status, chapter_id),
        )
        self.conn.commit()
        if row:
            self._recalc_word_count(row["manuscript_id"])

    def delete_chapter(self, chapter_id):
        cur = self.conn.execute(
            "SELECT manuscript_id FROM manuscript_chapters WHERE id = ?", (chapter_id,)
        )
        row = cur.fetchone()
        self.conn.execute("DELETE FROM manuscript_chapters WHERE id = ?", (chapter_id,))
        self.conn.commit()
        if row:
            self._recalc_word_count(row["manuscript_id"])

    def list_chapters(self, manuscript_id):
        cur = self.conn.execute(
            "SELECT * FROM manuscript_chapters WHERE manuscript_id = ? "
            "ORDER BY chapter_number",
            (manuscript_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_chapter(self, chapter_id):
        cur = self.conn.execute(
            "SELECT * FROM manuscript_chapters WHERE id = ?", (chapter_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Magic Systems
    # ------------------------------------------------------------------
    def create_magic_system(self, project_id, name, classification="",
                            description="", rules="", source="",
                            limitations="", cost=""):
        cur = self.conn.execute(
            "INSERT INTO magic_systems "
            "(project_id, name, classification, description, rules, source, "
            "limitations, cost, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, name.strip(), classification.strip(), description,
             rules, source.strip(), limitations, cost.strip(), self._now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_magic_system(self, magic_id, name, classification, description,
                            rules, source, limitations, cost):
        self.conn.execute(
            "UPDATE magic_systems SET name=?, classification=?, description=?, "
            "rules=?, source=?, limitations=?, cost=? WHERE id=?",
            (name.strip(), classification.strip(), description, rules,
             source.strip(), limitations, cost.strip(), magic_id),
        )
        self.conn.commit()

    def delete_magic_system(self, magic_id):
        self.conn.execute("DELETE FROM magic_systems WHERE id = ?", (magic_id,))
        self.conn.commit()

    def list_magic_systems(self, project_id):
        cur = self.conn.execute(
            "SELECT * FROM magic_systems WHERE project_id = ? ORDER BY name COLLATE NOCASE",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_magic_system(self, magic_id):
        cur = self.conn.execute(
            "SELECT * FROM magic_systems WHERE id = ?", (magic_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def replace_magic_abilities(self, magic_id, abilities):
        """Replace all abilities for a magic system.

        ``abilities`` is an iterable of (name, description, tier, notes).
        """
        self.conn.execute(
            "DELETE FROM magic_abilities WHERE magic_system_id = ?", (magic_id,)
        )
        for name, description, tier, notes in abilities:
            name = name.strip()
            if not name:
                continue
            self.conn.execute(
                "INSERT INTO magic_abilities "
                "(magic_system_id, name, description, tier, notes) VALUES (?, ?, ?, ?, ?)",
                (magic_id, name, description.strip(), tier.strip(), notes.strip()),
            )
        self.conn.commit()

    def list_magic_abilities(self, magic_id):
        cur = self.conn.execute(
            "SELECT * FROM magic_abilities WHERE magic_system_id = ? ORDER BY tier, name",
            (magic_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Religions
    # ------------------------------------------------------------------
    def create_religion(self, project_id, name, pantheon_type="", description="",
                        beliefs="", practices="", holy_texts="", afterlife_views=""):
        cur = self.conn.execute(
            "INSERT INTO religions "
            "(project_id, name, pantheon_type, description, beliefs, practices, "
            "holy_texts, afterlife_views, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, name.strip(), pantheon_type.strip(), description,
             beliefs, practices, holy_texts.strip(), afterlife_views, self._now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_religion(self, religion_id, name, pantheon_type, description,
                        beliefs, practices, holy_texts, afterlife_views):
        self.conn.execute(
            "UPDATE religions SET name=?, pantheon_type=?, description=?, "
            "beliefs=?, practices=?, holy_texts=?, afterlife_views=? WHERE id=?",
            (name.strip(), pantheon_type.strip(), description, beliefs,
             practices, holy_texts.strip(), afterlife_views, religion_id),
        )
        self.conn.commit()

    def delete_religion(self, religion_id):
        self.conn.execute("DELETE FROM religions WHERE id = ?", (religion_id,))
        self.conn.commit()

    def list_religions(self, project_id):
        cur = self.conn.execute(
            "SELECT * FROM religions WHERE project_id = ? ORDER BY name COLLATE NOCASE",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_religion(self, religion_id):
        cur = self.conn.execute(
            "SELECT * FROM religions WHERE id = ?", (religion_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def replace_religion_deities(self, religion_id, deities):
        """Replace all deities for a religion.

        ``deities`` is an iterable of (name, domain, description, alignment, notes).
        """
        self.conn.execute(
            "DELETE FROM religion_deities WHERE religion_id = ?", (religion_id,)
        )
        for name, domain, description, alignment, notes in deities:
            name = name.strip()
            if not name:
                continue
            self.conn.execute(
                "INSERT INTO religion_deities "
                "(religion_id, name, domain, description, alignment, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (religion_id, name, domain.strip(), description.strip(),
                 alignment.strip(), notes.strip()),
            )
        self.conn.commit()

    def list_religion_deities(self, religion_id):
        cur = self.conn.execute(
            "SELECT * FROM religion_deities WHERE religion_id = ? ORDER BY name",
            (religion_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export_project(self, project_id):
        """Compile the full record tree for a project into a JSON-ready dict."""
        project = self.get_project(project_id)
        if project is None:
            raise ValueError(f"No project with id {project_id}")

        characters = []
        for char in self.list_characters(project_id):
            attributes = {
                key: value
                for key, value in self.get_character_attributes(char["id"])
            }
            characters.append(
                {
                    "name": char["name"],
                    "role": char["role"],
                    "bio": char["bio"],
                    "created_at": char["created_at"],
                    "custom_attributes": attributes,
                }
            )

        languages = []
        for lang in self.list_languages(project_id):
            lexicon = [
                {
                    "word": entry["word"],
                    "translation": entry["translation"],
                    "part_of_speech": entry["part_of_speech"],
                    "notes": entry["notes"],
                }
                for entry in self.list_lexicon(lang["id"])
            ]
            languages.append(
                {
                    "name": lang["name"],
                    "grammar_documentation": lang["grammar"],
                    "created_at": lang["created_at"],
                    "lexicon": lexicon,
                }
            )

        locations = []
        for loc in self.list_locations(project_id):
            attrs = {k: v for k, v in self.get_location_attributes(loc["id"])}
            locations.append(
                {
                    "name": loc["name"],
                    "type": loc["type"],
                    "description": loc["description"],
                    "climate": loc["climate"],
                    "population": loc["population"],
                    "notes": loc["notes"],
                    "created_at": loc["created_at"],
                    "custom_attributes": attrs,
                }
            )

        events = []
        for evt in self.list_events(project_id):
            linked = [c["name"] for c in self.get_event_characters(evt["id"])]
            events.append(
                {
                    "title": evt["title"],
                    "event_type": evt["event_type"],
                    "date_label": evt["date_label"],
                    "description": evt["description"],
                    "notes": evt["notes"],
                    "created_at": evt["created_at"],
                    "linked_characters": linked,
                }
            )

        manuscripts = []
        for ms in self.list_manuscripts(project_id):
            chapters = [
                {
                    "chapter_number": ch["chapter_number"],
                    "title": ch["title"],
                    "body": ch["body"],
                    "notes": ch["notes"],
                    "status": ch["status"],
                }
                for ch in self.list_chapters(ms["id"])
            ]
            manuscripts.append(
                {
                    "title": ms["title"],
                    "genre": ms["genre"],
                    "synopsis": ms["synopsis"],
                    "status": ms["status"],
                    "word_count": ms["word_count"],
                    "created_at": ms["created_at"],
                    "updated_at": ms["updated_at"],
                    "chapters": chapters,
                }
            )

        magic_systems = []
        for ms in self.list_magic_systems(project_id):
            abilities = [
                {
                    "name": ab["name"],
                    "description": ab["description"],
                    "tier": ab["tier"],
                    "notes": ab["notes"],
                }
                for ab in self.list_magic_abilities(ms["id"])
            ]
            magic_systems.append(
                {
                    "name": ms["name"],
                    "classification": ms["classification"],
                    "description": ms["description"],
                    "rules": ms["rules"],
                    "source": ms["source"],
                    "limitations": ms["limitations"],
                    "cost": ms["cost"],
                    "created_at": ms["created_at"],
                    "abilities": abilities,
                }
            )

        religions = []
        for rel in self.list_religions(project_id):
            deities = [
                {
                    "name": d["name"],
                    "domain": d["domain"],
                    "description": d["description"],
                    "alignment": d["alignment"],
                    "notes": d["notes"],
                }
                for d in self.list_religion_deities(rel["id"])
            ]
            religions.append(
                {
                    "name": rel["name"],
                    "pantheon_type": rel["pantheon_type"],
                    "description": rel["description"],
                    "beliefs": rel["beliefs"],
                    "practices": rel["practices"],
                    "holy_texts": rel["holy_texts"],
                    "afterlife_views": rel["afterlife_views"],
                    "created_at": rel["created_at"],
                    "deities": deities,
                }
            )

        timeline = [
            {
                "name": era["name"],
                "start_label": era["start_label"],
                "end_label": era["end_label"],
                "description": era["description"],
                "sort_order": era["sort_order"],
                "created_at": era["created_at"],
            }
            for era in self.list_eras(project_id)
        ]

        creatures = [
            {
                "name": c["name"],
                "creature_type": c["creature_type"],
                "habitat": c["habitat"],
                "size": c["size"],
                "diet": c["diet"],
                "behaviour": c["behaviour"],
                "abilities": c["abilities"],
                "weaknesses": c["weaknesses"],
                "lore": c["lore"],
                "notes": c["notes"],
                "created_at": c["created_at"],
            }
            for c in self.list_creatures(project_id)
        ]

        return {
            "export_format": "campfire-studio-clone/2.0",
            "exported_at": self._now(),
            "project": {
                "name": project["name"],
                "description": project["description"],
                "created_at": project["created_at"],
            },
            "timeline": timeline,
            "characters": characters,
            "languages": languages,
            "locations": locations,
            "events": events,
            "creatures": creatures,
            "manuscripts": manuscripts,
            "magic_systems": magic_systems,
            "religions": religions,
        }

    # ------------------------------------------------------------------
    # Timeline Eras
    # ------------------------------------------------------------------
    def create_era(self, project_id, name, start_label="", end_label="",
                   description="", sort_order=0):
        cur = self.conn.execute(
            "INSERT INTO timeline_eras "
            "(project_id, name, start_label, end_label, description, sort_order, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, name.strip(), start_label.strip(), end_label.strip(),
             description, sort_order, self._now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_era(self, era_id, name, start_label, end_label, description, sort_order):
        self.conn.execute(
            "UPDATE timeline_eras SET name=?, start_label=?, end_label=?, "
            "description=?, sort_order=? WHERE id=?",
            (name.strip(), start_label.strip(), end_label.strip(),
             description, sort_order, era_id),
        )
        self.conn.commit()

    def delete_era(self, era_id):
        self.conn.execute("DELETE FROM timeline_eras WHERE id = ?", (era_id,))
        self.conn.commit()

    def list_eras(self, project_id):
        cur = self.conn.execute(
            "SELECT * FROM timeline_eras WHERE project_id = ? ORDER BY sort_order, name COLLATE NOCASE",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_era(self, era_id):
        cur = self.conn.execute("SELECT * FROM timeline_eras WHERE id = ?", (era_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Creatures
    # ------------------------------------------------------------------
    def create_creature(self, project_id, name, creature_type="", habitat="",
                        size="", diet="", behaviour="", abilities="",
                        weaknesses="", lore="", notes=""):
        cur = self.conn.execute(
            "INSERT INTO creatures "
            "(project_id, name, creature_type, habitat, size, diet, behaviour, "
            "abilities, weaknesses, lore, notes, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, name.strip(), creature_type.strip(), habitat.strip(),
             size.strip(), diet.strip(), behaviour, abilities, weaknesses,
             lore, notes, self._now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_creature(self, creature_id, name, creature_type, habitat, size,
                        diet, behaviour, abilities, weaknesses, lore, notes):
        self.conn.execute(
            "UPDATE creatures SET name=?, creature_type=?, habitat=?, size=?, diet=?, "
            "behaviour=?, abilities=?, weaknesses=?, lore=?, notes=? WHERE id=?",
            (name.strip(), creature_type.strip(), habitat.strip(), size.strip(),
             diet.strip(), behaviour, abilities, weaknesses, lore, notes, creature_id),
        )
        self.conn.commit()

    def delete_creature(self, creature_id):
        self.conn.execute("DELETE FROM creatures WHERE id = ?", (creature_id,))
        self.conn.commit()

    def list_creatures(self, project_id):
        cur = self.conn.execute(
            "SELECT * FROM creatures WHERE project_id = ? ORDER BY name COLLATE NOCASE",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_creature(self, creature_id):
        cur = self.conn.execute("SELECT * FROM creatures WHERE id = ?", (creature_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()


    # ------------------------------------------------------------------
    # Chapter revisions (snapshots for diff/restore)
    # ------------------------------------------------------------------
    def _ensure_revisions_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chapter_revisions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id   INTEGER NOT NULL,
                body         TEXT NOT NULL DEFAULT '',
                saved_at     TEXT NOT NULL,
                FOREIGN KEY (chapter_id) REFERENCES manuscript_chapters (id)
                    ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def save_chapter_revision(self, chapter_id, body):
        self._ensure_revisions_table()
        self.conn.execute(
            "INSERT INTO chapter_revisions (chapter_id, body, saved_at) VALUES (?, ?, ?)",
            (chapter_id, body, self._now()),
        )
        # Keep at most 50 snapshots per chapter
        self.conn.execute("""
            DELETE FROM chapter_revisions
            WHERE chapter_id = ? AND id NOT IN (
                SELECT id FROM chapter_revisions
                WHERE chapter_id = ?
                ORDER BY id DESC LIMIT 50
            )
        """, (chapter_id, chapter_id))
        self.conn.commit()

    def list_chapter_revisions(self, chapter_id):
        self._ensure_revisions_table()
        cur = self.conn.execute(
            "SELECT id, saved_at FROM chapter_revisions "
            "WHERE chapter_id = ? ORDER BY id DESC",
            (chapter_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_chapter_revision(self, revision_id):
        self._ensure_revisions_table()
        cur = self.conn.execute(
            "SELECT * FROM chapter_revisions WHERE id = ?", (revision_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Character relationships
    # ------------------------------------------------------------------
    def _ensure_relationships_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS character_relationships (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL,
                char_a_id       INTEGER NOT NULL,
                char_b_id       INTEGER NOT NULL,
                relationship    TEXT NOT NULL DEFAULT '',
                notes           TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (char_a_id)  REFERENCES characters (id) ON DELETE CASCADE,
                FOREIGN KEY (char_b_id)  REFERENCES characters (id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def upsert_relationship(self, project_id, char_a_id, char_b_id, relationship, notes=""):
        self._ensure_relationships_table()
        cur = self.conn.execute(
            "SELECT id FROM character_relationships "
            "WHERE project_id=? AND char_a_id=? AND char_b_id=?",
            (project_id, char_a_id, char_b_id),
        )
        row = cur.fetchone()
        if row:
            self.conn.execute(
                "UPDATE character_relationships SET relationship=?, notes=? WHERE id=?",
                (relationship, notes, row["id"]),
            )
        else:
            self.conn.execute(
                "INSERT INTO character_relationships "
                "(project_id, char_a_id, char_b_id, relationship, notes) "
                "VALUES (?, ?, ?, ?, ?)",
                (project_id, char_a_id, char_b_id, relationship, notes),
            )
        self.conn.commit()

    def delete_relationship(self, project_id, char_a_id, char_b_id):
        self._ensure_relationships_table()
        self.conn.execute(
            "DELETE FROM character_relationships "
            "WHERE project_id=? AND char_a_id=? AND char_b_id=?",
            (project_id, char_a_id, char_b_id),
        )
        self.conn.commit()

    def list_relationships(self, project_id):
        self._ensure_relationships_table()
        cur = self.conn.execute(
            "SELECT cr.*, "
            "ca.name AS char_a_name, cb.name AS char_b_name "
            "FROM character_relationships cr "
            "JOIN characters ca ON ca.id = cr.char_a_id "
            "JOIN characters cb ON cb.id = cr.char_b_id "
            "WHERE cr.project_id = ?",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # World map pins
    # ------------------------------------------------------------------
    def _ensure_map_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS world_map_pins (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL,
                location_id INTEGER,
                label       TEXT NOT NULL DEFAULT '',
                x           REAL NOT NULL DEFAULT 0.5,
                y           REAL NOT NULL DEFAULT 0.5,
                color       TEXT NOT NULL DEFAULT '#ffb454',
                FOREIGN KEY (project_id)  REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE SET NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS world_map_images (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL UNIQUE,
                image_data  BLOB,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def save_map_image(self, project_id, image_bytes):
        self._ensure_map_table()
        self.conn.execute(
            "INSERT OR REPLACE INTO world_map_images (project_id, image_data) VALUES (?, ?)",
            (project_id, image_bytes),
        )
        self.conn.commit()

    def get_map_image(self, project_id):
        self._ensure_map_table()
        cur = self.conn.execute(
            "SELECT image_data FROM world_map_images WHERE project_id = ?", (project_id,)
        )
        row = cur.fetchone()
        return row["image_data"] if row else None

    def upsert_map_pin(self, project_id, label, x, y, color="#ffb454", location_id=None, pin_id=None):
        self._ensure_map_table()
        if pin_id:
            self.conn.execute(
                "UPDATE world_map_pins SET label=?, x=?, y=?, color=?, location_id=? WHERE id=?",
                (label, x, y, color, location_id, pin_id),
            )
        else:
            self.conn.execute(
                "INSERT INTO world_map_pins (project_id, label, x, y, color, location_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, label, x, y, color, location_id),
            )
        self.conn.commit()

    def delete_map_pin(self, pin_id):
        self._ensure_map_table()
        self.conn.execute("DELETE FROM world_map_pins WHERE id = ?", (pin_id,))
        self.conn.commit()

    def list_map_pins(self, project_id):
        self._ensure_map_table()
        cur = self.conn.execute(
            "SELECT * FROM world_map_pins WHERE project_id = ?", (project_id,)
        )
        return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Scene conflict cards
    # ------------------------------------------------------------------
    def _ensure_scene_cards_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scene_cards (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id   INTEGER NOT NULL UNIQUE,
                goal         TEXT NOT NULL DEFAULT '',
                conflict     TEXT NOT NULL DEFAULT '',
                outcome      TEXT NOT NULL DEFAULT '',
                tension      INTEGER NOT NULL DEFAULT 3,
                FOREIGN KEY (chapter_id) REFERENCES manuscript_chapters (id)
                    ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def upsert_scene_card(self, chapter_id, goal, conflict, outcome, tension):
        self._ensure_scene_cards_table()
        self.conn.execute("""
            INSERT INTO scene_cards (chapter_id, goal, conflict, outcome, tension)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chapter_id) DO UPDATE SET
                goal=excluded.goal, conflict=excluded.conflict,
                outcome=excluded.outcome, tension=excluded.tension
        """, (chapter_id, goal, conflict, outcome, tension))
        self.conn.commit()

    def get_scene_card(self, chapter_id):
        self._ensure_scene_cards_table()
        cur = self.conn.execute(
            "SELECT * FROM scene_cards WHERE chapter_id = ?", (chapter_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def list_scene_cards_for_manuscript(self, manuscript_id):
        self._ensure_scene_cards_table()
        cur = self.conn.execute("""
            SELECT sc.*, mc.title AS chapter_title, mc.chapter_number
            FROM scene_cards sc
            JOIN manuscript_chapters mc ON mc.id = sc.chapter_id
            WHERE mc.manuscript_id = ?
            ORDER BY mc.chapter_number
        """, (manuscript_id,))
        return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Word goals
    # ------------------------------------------------------------------
    def _ensure_word_goals_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS word_goals (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id   INTEGER NOT NULL UNIQUE,
                daily_goal   INTEGER NOT NULL DEFAULT 500,
                total_goal   INTEGER NOT NULL DEFAULT 80000,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def upsert_word_goal(self, project_id, daily_goal, total_goal):
        self._ensure_word_goals_table()
        self.conn.execute("""
            INSERT INTO word_goals (project_id, daily_goal, total_goal)
            VALUES (?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                daily_goal=excluded.daily_goal, total_goal=excluded.total_goal
        """, (project_id, daily_goal, total_goal))
        self.conn.commit()

    def get_word_goal(self, project_id):
        self._ensure_word_goals_table()
        cur = self.conn.execute(
            "SELECT * FROM word_goals WHERE project_id = ?", (project_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else {"daily_goal": 500, "total_goal": 80000}

    # ------------------------------------------------------------------
    # Chapter event links
    # ------------------------------------------------------------------
    def _ensure_chapter_events_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chapter_events (
                chapter_id  INTEGER NOT NULL,
                event_id    INTEGER NOT NULL,
                PRIMARY KEY (chapter_id, event_id),
                FOREIGN KEY (chapter_id) REFERENCES manuscript_chapters (id) ON DELETE CASCADE,
                FOREIGN KEY (event_id)   REFERENCES events (id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def set_chapter_events(self, chapter_id, event_ids):
        self._ensure_chapter_events_table()
        self.conn.execute("DELETE FROM chapter_events WHERE chapter_id = ?", (chapter_id,))
        for eid in event_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO chapter_events (chapter_id, event_id) VALUES (?, ?)",
                (chapter_id, eid),
            )
        self.conn.commit()

    def get_chapter_events(self, chapter_id):
        self._ensure_chapter_events_table()
        cur = self.conn.execute("""
            SELECT e.* FROM events e
            JOIN chapter_events ce ON ce.event_id = e.id
            WHERE ce.chapter_id = ?
        """, (chapter_id,))
        return [dict(row) for row in cur.fetchall()]
