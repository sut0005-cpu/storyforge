"""
main.py
story forge — PyQt6 desktop application.

Modules:
  * Multi-project workspace backed by SQLite (database.py)
  * Characters module: profile, bio and custom metadata attributes
  * Languages module: grammar documentation + interactive lexicon grid
  * AI Assistant: Claude-powered writing assistant with project context
  * Export Workspace: bundles project JSON into a folder and zip archive
"""

import json
import os
import re
import shutil
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import threading
import urllib.request
import urllib.error
import urllib.parse
from PyQt6.QtCore import QTimer
from database import Database

SUPABASE_URL = "https://cdkisxurtrmaruwnbfjw.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_nrrtqoy7gIvmiYOZF0Ym3A_7TAWkj9K"

APP_TITLE = "story forge"
import sys, os

def get_app_data_dir():
    """Returns a persistent folder for app data, works both frozen and as script."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller EXE — use AppData/Roaming on Windows
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    else:
        # Running as a normal script
        base = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(base, "StoryForge")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

BASE_DIR = get_app_data_dir()
DARK_STYLESHEET = """
QWidget {
    background-color: #1e1f24;
    color: #e8e6e3;
    font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}
QMainWindow { background-color: #17181c; }
QTabWidget::pane { border: 1px solid #34363e; border-radius: 6px; }
QTabBar::tab {
    background: #26272e; color: #b9b6b1; padding: 8px 18px;
    border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px;
}
QTabBar::tab:selected { background: #3a3c46; color: #ffb454; }
QPushButton {
    background-color: #34363e; border: 1px solid #4a4d58;
    border-radius: 5px; padding: 7px 11px;
    min-height: 30px;
}
QPushButton:disabled { color: #777983; background-color: #292a30; }

QPushButton:hover { background-color: #444753; }
QPushButton:pressed { background-color: #2b2d34; }
QPushButton#accent {
    background-color: #b3541e; border-color: #d97734;
    color: #ffffff; font-weight: bold;
}
QPushButton#accent:hover { background-color: #d2691e; }
QLineEdit, QTextEdit, QComboBox {
    background-color: #26272e; border: 1px solid #4a4d58;
    border-radius: 5px; padding: 5px;
    selection-background-color: #b3541e;
}
QListWidget, QTableWidget {
    background-color: #232429; border: 1px solid #4a4d58;
    border-radius: 5px; alternate-background-color: #2a2b31;
}
QListWidget::item { padding: 6px; }
QListWidget::item:selected { background: #b3541e; color: #ffffff; }
QHeaderView::section {
    background-color: #2e3038; color: #ffb454;
    padding: 5px; border: none; border-right: 1px solid #4a4d58;
}
QTableWidget::item:selected { background: #b3541e; }
QSplitter::handle { background-color: #34363e; }
QLabel#sectionTitle { font-size: 17px; font-weight: bold; color: #ffb454; }
QLabel#statusHint { color: #8d8a85; font-style: italic; }
QComboBox QAbstractItemView { background-color: #26272e; }
QScrollBar:vertical { background: #1e1f24; width: 10px; }
QScrollBar::handle:vertical { background: #4a4d58; border-radius: 5px; }
QMessageBox { background-color: #26272e; }
"""


def safe_slug(text):
    cleaned = re.sub(r"[^A-Za-z0-9_\-]+", "_", text.strip())
    return cleaned.strip("_") or "project"


class AccountDialog(QDialog):
    """A proper sign-in / account-creation window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Story Forge Account")
        self.setModal(True)
        self.setMinimumWidth(390)
        layout = QVBoxLayout(self)
        heading = QLabel("Connect your Story Forge account")
        heading.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(heading)
        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItems(["Sign in", "Create account"])
        self.email = QLineEdit()
        self.email.setPlaceholderText("you@example.com")
        self.email.setClearButtonEnabled(True)
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(34)
        self.password.setClearButtonEnabled(True)
        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(
            lambda checked: self.password.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        form.addRow("Action", self.mode)
        form.addRow("Email", self.email)
        form.addRow("Password", self.password)
        form.addRow("", self.show_password)
        layout.addLayout(form)
        hint = QLabel("Your cloud files are private and access is controlled by your Supabase account and bucket policies.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9aa4b2;")
        layout.addWidget(hint)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Continue")
        self.buttons.accepted.connect(self._validate)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _validate(self):
        if not self.email.text().strip() or "@" not in self.email.text():
            QMessageBox.warning(self, "Email required", "Enter a valid email address.")
            return
        if len(self.password.text()) < 6:
            QMessageBox.warning(self, "Password required", "Enter a password with at least 6 characters.")
            return
        self.accept()


class CloudFilesDialog(QDialog):
    """Browse folders and download files from the signed-in user's bucket."""
    def __init__(self, parent, token: str, bucket: str, user_id: str):
        super().__init__(parent)
        self.token = token
        self.bucket = bucket
        self.user_id = user_id
        self.prefix = user_id.strip("/") + "/" if user_id else ""
        self.setWindowTitle("Story Forge — Cloud Files")
        self.resize(640, 460)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Supabase Storage bucket: {bucket}"))
        self.location_label = QLabel("/ (bucket root)")
        self.location_label.setStyleSheet("color: #ffb454;")
        layout.addWidget(self.location_label)
        self.files = QListWidget()
        self.files.setAlternatingRowColors(True)
        self.files.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.files, 1)
        row = QHBoxLayout()
        self.back_btn = QPushButton("Up one folder")
        self.back_btn.clicked.connect(self.go_up)
        row.addWidget(self.back_btn)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self.refresh_btn)
        self.download_btn = QPushButton("Download selected")
        self.download_btn.clicked.connect(self.download_selected)
        row.addWidget(self.download_btn)
        row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row.addWidget(close_btn)
        layout.addLayout(row)
        self.refresh()

    def refresh(self):
        self.files.clear()
        self.location_label.setText("My files" + (" / " + self.prefix[len(self.user_id) + 1:] if self.user_id and self.prefix != self.user_id + "/" else ""))
        self.back_btn.setEnabled(bool(self.prefix) and self.prefix.rstrip("/") != self.user_id.rstrip("/"))
        try:
            from storage_client import list_project_files
            entries = list_project_files(self.token, self.bucket, self.prefix)
            if not entries:
                self.files.addItem("This folder is empty.")
                return
            for entry in entries:
                name = entry.get("name") or entry.get("id") or "(unnamed object)"
                is_folder = entry.get("id") is None and entry.get("metadata") is None
                display = ("📁  " if is_folder else "📄  ") + name
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, {
                    "name": name,
                    "folder": is_folder,
                    "key": self.prefix + name + ("/" if is_folder else ""),
                })
                self.files.addItem(item)
        except Exception as exc:
            QMessageBox.critical(self, "Could not list cloud files", str(exc))

    def _open_item(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and data.get("folder"):
            self.prefix = data["key"]
            self.refresh()
        elif data:
            self.download_selected()

    def go_up(self):
        if not self.prefix:
            return
        parent = self.prefix.rstrip("/").rsplit("/", 1)[0]
        self.prefix = (parent + "/") if parent else ""
        self.refresh()

    def download_selected(self):
        item = self.files.currentItem()
        data = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not data or data.get("folder"):
            QMessageBox.information(self, "Select a file", "Choose a file (not a folder) first.")
            return
        object_key = data["key"]
        local_path, _ = QFileDialog.getSaveFileName(self, "Save cloud file", os.path.basename(object_key))
        if not local_path:
            return
        try:
            from storage_client import download_project_file
            download_project_file(object_key, local_path, self.token, self.bucket)
            QMessageBox.information(self, "Download complete", f"Saved file to:\n{local_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Download failed", str(exc))


class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_project_id = None
        self.current_character_id = None
        self.current_language_id = None
        self.current_location_id = None
        self.current_event_id = None
        self.current_creature_id = None
        self.current_magic_id = None
        self.current_religion_id = None
        self.current_era_id = None
        self.current_manuscript_id = None
        self.current_chapter_id = None
        self._ai_thread = None
        self._supabase_access_token = None
        self._supabase_user_id = None
        self._supabase_email = None
        self._cloud_sync_busy = False
        self._cloud_last_payload = None

        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)
        self._build_ui()
        self._reload_projects()
        self._cloud_timer = QTimer(self)
        self._cloud_timer.setInterval(30000)
        self._cloud_timer.timeout.connect(self._cloud_auto_sync)
        self._cloud_timer.start()

    # ------------------------------------------------------------------
    # UI scaffolding
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Row 1: workspace and export actions.
        workspace_bar = QHBoxLayout()
        workspace_bar.setSpacing(8)

        title = QLabel("Story Forge")
        title.setObjectName("sectionTitle")
        workspace_bar.addWidget(title)
        workspace_bar.addSpacing(12)
        workspace_bar.addWidget(QLabel("Project:"))

        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(170)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        workspace_bar.addWidget(self.project_combo, 1)

        new_project_btn = QPushButton("New Project")
        new_project_btn.clicked.connect(self._create_project)
        workspace_bar.addWidget(new_project_btn)

        delete_project_btn = QPushButton("Delete Project")
        delete_project_btn.clicked.connect(self._delete_project)
        workspace_bar.addWidget(delete_project_btn)

        export_btn = QPushButton("Export Workspace")
        export_btn.setObjectName("accent")
        export_btn.clicked.connect(self._export_workspace)
        workspace_bar.addWidget(export_btn)

        export_docx_btn = QPushButton("Export Sections (DOCX)")
        export_docx_btn.clicked.connect(self._export_sections_docx)
        workspace_bar.addWidget(export_docx_btn)
        root.addLayout(workspace_bar)

        # Row 2: cloud account and sync actions. Keeping these separate
        # prevents long labels being squeezed or clipped on smaller windows.
        cloud_bar = QHBoxLayout()
        cloud_bar.setSpacing(8)

        cloud_upload_btn = QPushButton("Upload File to Cloud")
        cloud_upload_btn.clicked.connect(self._cloud_upload_file)
        cloud_bar.addWidget(cloud_upload_btn)

        cloud_download_btn = QPushButton("Browse Cloud Files")
        cloud_download_btn.clicked.connect(self._cloud_download_file)
        cloud_bar.addWidget(cloud_download_btn)

        self.account_btn = QPushButton("Story Forge Account: Sign In")
        self.account_btn.clicked.connect(self._cloud_account_dialog)
        cloud_bar.addWidget(self.account_btn)

        self.sync_btn = QPushButton("Sync Cloud Now")
        self.sync_btn.clicked.connect(self._cloud_sync_now)
        cloud_bar.addWidget(self.sync_btn)

        cloud_bar.addStretch(1)
        root.addLayout(cloud_bar)

        # --- Tabs ---
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_timeline_tab(), "Timeline")
        self.tabs.addTab(self._build_characters_tab(), "Characters")
        self.tabs.addTab(self._build_locations_tab(), "Locations")
        self.tabs.addTab(self._build_events_tab(), "Events")
        self.tabs.addTab(self._build_creatures_tab(), "Creatures")
        self.tabs.addTab(self._build_magic_tab(), "Magic Systems")
        self.tabs.addTab(self._build_religions_tab(), "Religions")
        self.tabs.addTab(self._build_languages_tab(), "Languages")
        self.tabs.addTab(self._build_manuscripts_tab(), "Manuscripts")
        self.tabs.addTab(self._build_font_studio_tab(), "Font Studio")
        root.addWidget(self.tabs, 1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------------
    # Characters tab
    # ------------------------------------------------------------------
    def _build_characters_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: list + controls
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Cast"))
        self.character_list = QListWidget()
        self.character_list.itemSelectionChanged.connect(self._on_character_selected)
        left_layout.addWidget(self.character_list, 1)

        char_buttons = QHBoxLayout()
        add_char_btn = QPushButton("New")
        add_char_btn.clicked.connect(self._new_character)
        del_char_btn = QPushButton("Delete")
        del_char_btn.clicked.connect(self._delete_character)
        char_buttons.addWidget(add_char_btn)
        char_buttons.addWidget(del_char_btn)
        left_layout.addLayout(char_buttons)

        # Right: profile editor
        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.char_name_edit = QLineEdit()
        self.char_role_edit = QLineEdit()
        form.addRow("Name:", self.char_name_edit)
        form.addRow("Role / Archetype:", self.char_role_edit)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("Biography"))
        self.char_bio_edit = QTextEdit()
        self.char_bio_edit.setPlaceholderText(
            "Backstory, motivations, secrets, narrative arcs..."
        )
        right_layout.addWidget(self.char_bio_edit, 2)

        right_layout.addWidget(QLabel("Custom Metadata Attributes"))
        self.char_attr_table = QTableWidget(0, 2)
        self.char_attr_table.setHorizontalHeaderLabels(["Attribute", "Value"])
        self.char_attr_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        right_layout.addWidget(self.char_attr_table, 2)

        attr_buttons = QHBoxLayout()
        add_attr_btn = QPushButton("Add Attribute")
        add_attr_btn.clicked.connect(self._add_attribute_row)
        remove_attr_btn = QPushButton("Remove Selected Attribute")
        remove_attr_btn.clicked.connect(self._remove_attribute_row)
        attr_buttons.addWidget(add_attr_btn)
        attr_buttons.addWidget(remove_attr_btn)
        attr_buttons.addStretch(1)
        save_char_btn = QPushButton("Save Character")
        save_char_btn.setObjectName("accent")
        save_char_btn.clicked.connect(self._save_character)
        attr_buttons.addWidget(save_char_btn)
        right_layout.addLayout(attr_buttons)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        return widget

    def _new_character(self):
        if not self._require_project():
            return
        name, ok = QInputDialog.getText(self, "New Character", "Character name:")
        if not ok or not name.strip():
            return
        char_id = self.db.create_character(self.current_project_id, name)
        self._reload_characters(select_id=char_id)
        self.statusBar().showMessage(f"Character '{name.strip()}' created")

    def _delete_character(self):
        if self.current_character_id is None:
            return
        char = self.db.get_character(self.current_character_id)
        confirm = QMessageBox.question(
            self,
            "Delete Character",
            f"Delete '{char['name']}' and all of their attributes?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_character(self.current_character_id)
            self.current_character_id = None
            self._reload_characters()
            self._clear_character_form()

    def _save_character(self):
        if self.current_character_id is None:
            QMessageBox.information(
                self, APP_TITLE, "Select or create a character first."
            )
            return
        name = self.char_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, APP_TITLE, "Character name cannot be empty.")
            return
        self.db.update_character(
            self.current_character_id,
            name,
            self.char_role_edit.text(),
            self.char_bio_edit.toPlainText(),
        )
        pairs = []
        for row in range(self.char_attr_table.rowCount()):
            key_item = self.char_attr_table.item(row, 0)
            value_item = self.char_attr_table.item(row, 1)
            key = key_item.text() if key_item else ""
            value = value_item.text() if value_item else ""
            pairs.append((key, value))
        self.db.set_character_attributes(self.current_character_id, pairs)
        self._reload_characters(select_id=self.current_character_id)
        self.statusBar().showMessage(f"Saved character '{name}'")

    def _on_character_selected(self):
        items = self.character_list.selectedItems()
        if not items:
            return
        char_id = items[0].data(Qt.ItemDataRole.UserRole)
        self.current_character_id = char_id
        char = self.db.get_character(char_id)
        if char is None:
            return
        self.char_name_edit.setText(char["name"])
        self.char_role_edit.setText(char["role"])
        self.char_bio_edit.setPlainText(char["bio"])
        self.char_attr_table.setRowCount(0)
        for key, value in self.db.get_character_attributes(char_id):
            row = self.char_attr_table.rowCount()
            self.char_attr_table.insertRow(row)
            self.char_attr_table.setItem(row, 0, QTableWidgetItem(key))
            self.char_attr_table.setItem(row, 1, QTableWidgetItem(value))

    def _add_attribute_row(self):
        row = self.char_attr_table.rowCount()
        self.char_attr_table.insertRow(row)
        self.char_attr_table.setItem(row, 0, QTableWidgetItem(""))
        self.char_attr_table.setItem(row, 1, QTableWidgetItem(""))
        self.char_attr_table.editItem(self.char_attr_table.item(row, 0))

    def _remove_attribute_row(self):
        row = self.char_attr_table.currentRow()
        if row >= 0:
            self.char_attr_table.removeRow(row)

    def _clear_character_form(self):
        self.char_name_edit.clear()
        self.char_role_edit.clear()
        self.char_bio_edit.clear()
        self.char_attr_table.setRowCount(0)

    def _reload_characters(self, select_id=None):
        self.character_list.blockSignals(True)
        self.character_list.clear()
        if self.current_project_id is not None:
            for char in self.db.list_characters(self.current_project_id):
                item = QListWidgetItem(char["name"])
                item.setData(Qt.ItemDataRole.UserRole, char["id"])
                self.character_list.addItem(item)
                if select_id is not None and char["id"] == select_id:
                    item.setSelected(True)
        self.character_list.blockSignals(False)
        if select_id is not None:
            self._on_character_selected()

    # ------------------------------------------------------------------
    # Languages tab
    # ------------------------------------------------------------------
    def _build_languages_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Constructed Languages"))
        self.language_list = QListWidget()
        self.language_list.itemSelectionChanged.connect(self._on_language_selected)
        left_layout.addWidget(self.language_list, 1)

        lang_buttons = QHBoxLayout()
        add_lang_btn = QPushButton("New")
        add_lang_btn.clicked.connect(self._new_language)
        del_lang_btn = QPushButton("Delete")
        del_lang_btn.clicked.connect(self._delete_language)
        lang_buttons.addWidget(add_lang_btn)
        lang_buttons.addWidget(del_lang_btn)
        left_layout.addLayout(lang_buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.lang_name_edit = QLineEdit()
        form.addRow("Language name:", self.lang_name_edit)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("Grammar Documentation"))
        self.lang_grammar_edit = QTextEdit()
        self.lang_grammar_edit.setPlaceholderText(
            "Phonology, morphology, syntax rules, sample sentences..."
        )
        right_layout.addWidget(self.lang_grammar_edit, 2)

        right_layout.addWidget(QLabel("Lexicon Dictionary"))
        self.lexicon_table = QTableWidget(0, 4)
        self.lexicon_table.setHorizontalHeaderLabels(
            ["Word", "Translation", "Part of Speech", "Notes"]
        )
        self.lexicon_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.lexicon_table.setAlternatingRowColors(True)
        right_layout.addWidget(self.lexicon_table, 3)

        lex_buttons = QHBoxLayout()
        add_entry_btn = QPushButton("Add Entry")
        add_entry_btn.clicked.connect(self._add_lexicon_row)
        remove_entry_btn = QPushButton("Remove Selected Entry")
        remove_entry_btn.clicked.connect(self._remove_lexicon_row)
        lex_buttons.addWidget(add_entry_btn)
        lex_buttons.addWidget(remove_entry_btn)
        lex_buttons.addStretch(1)
        save_lang_btn = QPushButton("Save Language")
        save_lang_btn.setObjectName("accent")
        save_lang_btn.clicked.connect(self._save_language)
        lex_buttons.addWidget(save_lang_btn)
        right_layout.addLayout(lex_buttons)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        return widget

    def _new_language(self):
        if not self._require_project():
            return
        name, ok = QInputDialog.getText(self, "New Language", "Language name:")
        if not ok or not name.strip():
            return
        lang_id = self.db.create_language(self.current_project_id, name)
        self._reload_languages(select_id=lang_id)
        self.statusBar().showMessage(f"Language '{name.strip()}' created")

    def _delete_language(self):
        if self.current_language_id is None:
            return
        lang = self.db.get_language(self.current_language_id)
        confirm = QMessageBox.question(
            self,
            "Delete Language",
            f"Delete '{lang['name']}' and its entire lexicon?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_language(self.current_language_id)
            self.current_language_id = None
            self._reload_languages()
            self._clear_language_form()

    def _save_language(self):
        if self.current_language_id is None:
            QMessageBox.information(
                self, APP_TITLE, "Select or create a language first."
            )
            return
        name = self.lang_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, APP_TITLE, "Language name cannot be empty.")
            return
        self.db.update_language(
            self.current_language_id, name, self.lang_grammar_edit.toPlainText()
        )
        entries = []
        for row in range(self.lexicon_table.rowCount()):
            values = []
            for col in range(4):
                item = self.lexicon_table.item(row, col)
                values.append(item.text() if item else "")
            entries.append(tuple(values))
        self.db.replace_lexicon(self.current_language_id, entries)
        self._reload_languages(select_id=self.current_language_id)
        self.statusBar().showMessage(f"Saved language '{name}'")

    def _on_language_selected(self):
        items = self.language_list.selectedItems()
        if not items:
            return
        lang_id = items[0].data(Qt.ItemDataRole.UserRole)
        self.current_language_id = lang_id
        lang = self.db.get_language(lang_id)
        if lang is None:
            return
        self.lang_name_edit.setText(lang["name"])
        self.lang_grammar_edit.setPlainText(lang["grammar"])
        self.lexicon_table.setRowCount(0)
        for entry in self.db.list_lexicon(lang_id):
            row = self.lexicon_table.rowCount()
            self.lexicon_table.insertRow(row)
            self.lexicon_table.setItem(row, 0, QTableWidgetItem(entry["word"]))
            self.lexicon_table.setItem(row, 1, QTableWidgetItem(entry["translation"]))
            self.lexicon_table.setItem(
                row, 2, QTableWidgetItem(entry["part_of_speech"])
            )
            self.lexicon_table.setItem(row, 3, QTableWidgetItem(entry["notes"]))

    def _add_lexicon_row(self):
        row = self.lexicon_table.rowCount()
        self.lexicon_table.insertRow(row)
        for col in range(4):
            self.lexicon_table.setItem(row, col, QTableWidgetItem(""))
        self.lexicon_table.editItem(self.lexicon_table.item(row, 0))

    def _remove_lexicon_row(self):
        row = self.lexicon_table.currentRow()
        if row >= 0:
            self.lexicon_table.removeRow(row)

    def _clear_language_form(self):
        self.lang_name_edit.clear()
        self.lang_grammar_edit.clear()
        self.lexicon_table.setRowCount(0)

    def _reload_languages(self, select_id=None):
        self.language_list.blockSignals(True)
        self.language_list.clear()
        if self.current_project_id is not None:
            for lang in self.db.list_languages(self.current_project_id):
                item = QListWidgetItem(lang["name"])
                item.setData(Qt.ItemDataRole.UserRole, lang["id"])
                self.language_list.addItem(item)
                if select_id is not None and lang["id"] == select_id:
                    item.setSelected(True)
        self.language_list.blockSignals(False)
        if select_id is not None:
            self._on_language_selected()

    # ------------------------------------------------------------------
    # Timeline tab
    # ------------------------------------------------------------------
    def _build_timeline_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Eras & Ages"))
        self.era_list = QListWidget()
        self.era_list.itemSelectionChanged.connect(self._on_era_selected)
        left_layout.addWidget(self.era_list, 1)

        era_buttons = QHBoxLayout()
        add_era_btn = QPushButton("New")
        add_era_btn.clicked.connect(self._new_era)
        del_era_btn = QPushButton("Delete")
        del_era_btn.clicked.connect(self._delete_era)
        era_buttons.addWidget(add_era_btn)
        era_buttons.addWidget(del_era_btn)
        left_layout.addLayout(era_buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.era_name_edit = QLineEdit()
        self.era_start_edit = QLineEdit()
        self.era_start_edit.setPlaceholderText("e.g. Year 0 / Age of Dawn")
        self.era_end_edit = QLineEdit()
        self.era_end_edit.setPlaceholderText("e.g. Year 500 / Collapse")
        self.era_order_edit = QLineEdit("0")
        self.era_order_edit.setPlaceholderText("Sort order (integer)")
        form.addRow("Era Name:", self.era_name_edit)
        form.addRow("Start:", self.era_start_edit)
        form.addRow("End:", self.era_end_edit)
        form.addRow("Sort Order:", self.era_order_edit)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("Description"))
        self.era_desc_edit = QTextEdit()
        self.era_desc_edit.setPlaceholderText(
            "What defines this era? Major shifts in power, magic, culture..."
        )
        right_layout.addWidget(self.era_desc_edit, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        save_era_btn = QPushButton("Save Era")
        save_era_btn.setObjectName("accent")
        save_era_btn.clicked.connect(self._save_era)
        btn_row.addWidget(save_era_btn)
        right_layout.addLayout(btn_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        return widget

    def _new_era(self):
        if not self._require_project():
            return
        name, ok = QInputDialog.getText(self, "New Era", "Era name:")
        if not ok or not name.strip():
            return
        era_id = self.db.create_era(self.current_project_id, name)
        self._reload_eras(select_id=era_id)
        self.statusBar().showMessage(f"Era '{name.strip()}' created")

    def _delete_era(self):
        if self.current_era_id is None:
            return
        era = self.db.get_era(self.current_era_id)
        confirm = QMessageBox.question(
            self, "Delete Era", f"Delete '{era['name']}'?"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_era(self.current_era_id)
            self.current_era_id = None
            self._reload_eras()
            self._clear_era_form()

    def _save_era(self):
        if self.current_era_id is None:
            QMessageBox.information(self, APP_TITLE, "Select or create an era first.")
            return
        name = self.era_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, APP_TITLE, "Era name cannot be empty.")
            return
        try:
            sort_order = int(self.era_order_edit.text().strip() or "0")
        except ValueError:
            sort_order = 0
        self.db.update_era(
            self.current_era_id, name,
            self.era_start_edit.text(),
            self.era_end_edit.text(),
            self.era_desc_edit.toPlainText(),
            sort_order,
        )
        self._reload_eras(select_id=self.current_era_id)
        self.statusBar().showMessage(f"Saved era '{name}'")

    def _on_era_selected(self):
        items = self.era_list.selectedItems()
        if not items:
            return
        era_id = items[0].data(Qt.ItemDataRole.UserRole)
        self.current_era_id = era_id
        era = self.db.get_era(era_id)
        if era is None:
            return
        self.era_name_edit.setText(era["name"])
        self.era_start_edit.setText(era["start_label"])
        self.era_end_edit.setText(era["end_label"])
        self.era_order_edit.setText(str(era["sort_order"]))
        self.era_desc_edit.setPlainText(era["description"])

    def _clear_era_form(self):
        self.era_name_edit.clear()
        self.era_start_edit.clear()
        self.era_end_edit.clear()
        self.era_order_edit.setText("0")
        self.era_desc_edit.clear()

    def _reload_eras(self, select_id=None):
        self.era_list.blockSignals(True)
        self.era_list.clear()
        if self.current_project_id is not None:
            for era in self.db.list_eras(self.current_project_id):
                label = era["name"]
                if era["start_label"] or era["end_label"]:
                    label += f"  [{era['start_label']} – {era['end_label']}]"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, era["id"])
                self.era_list.addItem(item)
                if select_id is not None and era["id"] == select_id:
                    item.setSelected(True)
        self.era_list.blockSignals(False)
        if select_id is not None:
            self._on_era_selected()

    # ------------------------------------------------------------------
    # Locations tab
    # ------------------------------------------------------------------
    def _build_locations_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Locations"))
        self.location_list = QListWidget()
        self.location_list.itemSelectionChanged.connect(self._on_location_selected)
        left_layout.addWidget(self.location_list, 1)

        loc_buttons = QHBoxLayout()
        add_loc_btn = QPushButton("New")
        add_loc_btn.clicked.connect(self._new_location)
        del_loc_btn = QPushButton("Delete")
        del_loc_btn.clicked.connect(self._delete_location)
        loc_buttons.addWidget(add_loc_btn)
        loc_buttons.addWidget(del_loc_btn)
        left_layout.addLayout(loc_buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.loc_name_edit = QLineEdit()
        self.loc_type_edit = QLineEdit()
        self.loc_type_edit.setPlaceholderText("City, Forest, Dungeon, Realm…")
        self.loc_climate_edit = QLineEdit()
        self.loc_population_edit = QLineEdit()
        form.addRow("Name:", self.loc_name_edit)
        form.addRow("Type:", self.loc_type_edit)
        form.addRow("Climate:", self.loc_climate_edit)
        form.addRow("Population:", self.loc_population_edit)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("Description"))
        self.loc_desc_edit = QTextEdit()
        self.loc_desc_edit.setPlaceholderText("Geography, architecture, culture, history…")
        right_layout.addWidget(self.loc_desc_edit, 2)

        right_layout.addWidget(QLabel("Notes"))
        self.loc_notes_edit = QTextEdit()
        self.loc_notes_edit.setMaximumHeight(80)
        self.loc_notes_edit.setPlaceholderText("Secrets, plot hooks, DM notes…")
        right_layout.addWidget(self.loc_notes_edit)

        right_layout.addWidget(QLabel("Custom Attributes"))
        self.loc_attr_table = QTableWidget(0, 2)
        self.loc_attr_table.setHorizontalHeaderLabels(["Attribute", "Value"])
        self.loc_attr_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.loc_attr_table.setMaximumHeight(120)
        right_layout.addWidget(self.loc_attr_table)

        btn_row = QHBoxLayout()
        add_attr_btn = QPushButton("Add Attribute")
        add_attr_btn.clicked.connect(self._add_loc_attr_row)
        rm_attr_btn = QPushButton("Remove Attribute")
        rm_attr_btn.clicked.connect(self._remove_loc_attr_row)
        btn_row.addWidget(add_attr_btn)
        btn_row.addWidget(rm_attr_btn)
        btn_row.addStretch(1)
        save_loc_btn = QPushButton("Save Location")
        save_loc_btn.setObjectName("accent")
        save_loc_btn.clicked.connect(self._save_location)
        btn_row.addWidget(save_loc_btn)
        right_layout.addLayout(btn_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        return widget

    def _new_location(self):
        if not self._require_project():
            return
        name, ok = QInputDialog.getText(self, "New Location", "Location name:")
        if not ok or not name.strip():
            return
        loc_id = self.db.create_location(self.current_project_id, name)
        self._reload_locations(select_id=loc_id)
        self._refresh_event_location_combo()
        self.statusBar().showMessage(f"Location '{name.strip()}' created")

    def _delete_location(self):
        if self.current_location_id is None:
            return
        loc = self.db.get_location(self.current_location_id)
        confirm = QMessageBox.question(
            self, "Delete Location", f"Delete '{loc['name']}'?"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_location(self.current_location_id)
            self.current_location_id = None
            self._reload_locations()
            self._clear_location_form()
            self._refresh_event_location_combo()

    def _save_location(self):
        if self.current_location_id is None:
            QMessageBox.information(self, APP_TITLE, "Select or create a location first.")
            return
        name = self.loc_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, APP_TITLE, "Location name cannot be empty.")
            return
        self.db.update_location(
            self.current_location_id, name,
            self.loc_type_edit.text(),
            self.loc_desc_edit.toPlainText(),
            self.loc_climate_edit.text(),
            self.loc_population_edit.text(),
            self.loc_notes_edit.toPlainText(),
        )
        pairs = []
        for row in range(self.loc_attr_table.rowCount()):
            k = self.loc_attr_table.item(row, 0)
            v = self.loc_attr_table.item(row, 1)
            pairs.append((k.text() if k else "", v.text() if v else ""))
        self.db.set_location_attributes(self.current_location_id, pairs)
        self._reload_locations(select_id=self.current_location_id)
        self._refresh_event_location_combo()
        self.statusBar().showMessage(f"Saved location '{name}'")

    def _on_location_selected(self):
        items = self.location_list.selectedItems()
        if not items:
            return
        loc_id = items[0].data(Qt.ItemDataRole.UserRole)
        self.current_location_id = loc_id
        loc = self.db.get_location(loc_id)
        if loc is None:
            return
        self.loc_name_edit.setText(loc["name"])
        self.loc_type_edit.setText(loc["type"])
        self.loc_climate_edit.setText(loc["climate"])
        self.loc_population_edit.setText(loc["population"])
        self.loc_desc_edit.setPlainText(loc["description"])
        self.loc_notes_edit.setPlainText(loc["notes"])
        self.loc_attr_table.setRowCount(0)
        for key, value in self.db.get_location_attributes(loc_id):
            row = self.loc_attr_table.rowCount()
            self.loc_attr_table.insertRow(row)
            self.loc_attr_table.setItem(row, 0, QTableWidgetItem(key))
            self.loc_attr_table.setItem(row, 1, QTableWidgetItem(value))

    def _add_loc_attr_row(self):
        row = self.loc_attr_table.rowCount()
        self.loc_attr_table.insertRow(row)
        self.loc_attr_table.setItem(row, 0, QTableWidgetItem(""))
        self.loc_attr_table.setItem(row, 1, QTableWidgetItem(""))

    def _remove_loc_attr_row(self):
        row = self.loc_attr_table.currentRow()
        if row >= 0:
            self.loc_attr_table.removeRow(row)

    def _clear_location_form(self):
        self.loc_name_edit.clear()
        self.loc_type_edit.clear()
        self.loc_climate_edit.clear()
        self.loc_population_edit.clear()
        self.loc_desc_edit.clear()
        self.loc_notes_edit.clear()
        self.loc_attr_table.setRowCount(0)

    def _reload_locations(self, select_id=None):
        self.location_list.blockSignals(True)
        self.location_list.clear()
        if self.current_project_id is not None:
            for loc in self.db.list_locations(self.current_project_id):
                item = QListWidgetItem(loc["name"])
                item.setData(Qt.ItemDataRole.UserRole, loc["id"])
                self.location_list.addItem(item)
                if select_id is not None and loc["id"] == select_id:
                    item.setSelected(True)
        self.location_list.blockSignals(False)
        if select_id is not None:
            self._on_location_selected()

    # ------------------------------------------------------------------
    # Events tab
    # ------------------------------------------------------------------
    def _build_events_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Events"))
        self.event_list = QListWidget()
        self.event_list.itemSelectionChanged.connect(self._on_event_selected)
        left_layout.addWidget(self.event_list, 1)

        evt_buttons = QHBoxLayout()
        add_evt_btn = QPushButton("New")
        add_evt_btn.clicked.connect(self._new_event)
        del_evt_btn = QPushButton("Delete")
        del_evt_btn.clicked.connect(self._delete_event)
        evt_buttons.addWidget(add_evt_btn)
        evt_buttons.addWidget(del_evt_btn)
        left_layout.addLayout(evt_buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.evt_title_edit = QLineEdit()
        self.evt_type_edit = QLineEdit()
        self.evt_type_edit.setPlaceholderText("Battle, Discovery, Birth, Prophecy…")
        self.evt_date_edit = QLineEdit()
        self.evt_date_edit.setPlaceholderText("e.g. Year 342 / Third Age")
        self.evt_location_combo = QComboBox()
        form.addRow("Title:", self.evt_title_edit)
        form.addRow("Event Type:", self.evt_type_edit)
        form.addRow("Date / Period:", self.evt_date_edit)
        form.addRow("Location:", self.evt_location_combo)
        right_layout.addLayout(form)

        right_layout.addWidget(QLabel("Description"))
        self.evt_desc_edit = QTextEdit()
        self.evt_desc_edit.setPlaceholderText("What happened? Causes, outcomes, aftermath…")
        right_layout.addWidget(self.evt_desc_edit, 2)

        right_layout.addWidget(QLabel("Notes"))
        self.evt_notes_edit = QTextEdit()
        self.evt_notes_edit.setMaximumHeight(70)
        right_layout.addWidget(self.evt_notes_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        save_evt_btn = QPushButton("Save Event")
        save_evt_btn.setObjectName("accent")
        save_evt_btn.clicked.connect(self._save_event)
        btn_row.addWidget(save_evt_btn)
        right_layout.addLayout(btn_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        return widget

    def _refresh_event_location_combo(self):
        self.evt_location_combo.blockSignals(True)
        self.evt_location_combo.clear()
        self.evt_location_combo.addItem("— None —", None)
        if self.current_project_id is not None:
            for loc in self.db.list_locations(self.current_project_id):
                self.evt_location_combo.addItem(loc["name"], loc["id"])
        self.evt_location_combo.blockSignals(False)

    def _new_event(self):
        if not self._require_project():
            return
        title, ok = QInputDialog.getText(self, "New Event", "Event title:")
        if not ok or not title.strip():
            return
        evt_id = self.db.create_event(self.current_project_id, title)
        self._reload_events(select_id=evt_id)
        self.statusBar().showMessage(f"Event '{title.strip()}' created")

    def _delete_event(self):
        if self.current_event_id is None:
            return
        evt = self.db.get_event(self.current_event_id)
        confirm = QMessageBox.question(
            self, "Delete Event", f"Delete '{evt['title']}'?"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_event(self.current_event_id)
            self.current_event_id = None
            self._reload_events()
            self._clear_event_form()

    def _save_event(self):
        if self.current_event_id is None:
            QMessageBox.information(self, APP_TITLE, "Select or create an event first.")
            return
        title = self.evt_title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, APP_TITLE, "Event title cannot be empty.")
            return
        loc_id = self.evt_location_combo.currentData()
        self.db.update_event(
            self.current_event_id, title,
            self.evt_type_edit.text(),
            self.evt_date_edit.text(),
            self.evt_desc_edit.toPlainText(),
            loc_id,
            self.evt_notes_edit.toPlainText(),
        )
        self._reload_events(select_id=self.current_event_id)
        self.statusBar().showMessage(f"Saved event '{title}'")

    def _on_event_selected(self):
        items = self.event_list.selectedItems()
        if not items:
            return
        evt_id = items[0].data(Qt.ItemDataRole.UserRole)
        self.current_event_id = evt_id
        evt = self.db.get_event(evt_id)
        if evt is None:
            return
        self._refresh_event_location_combo()
        self.evt_title_edit.setText(evt["title"])
        self.evt_type_edit.setText(evt["event_type"])
        self.evt_date_edit.setText(evt["date_label"])
        self.evt_desc_edit.setPlainText(evt["description"])
        self.evt_notes_edit.setPlainText(evt["notes"])
        idx = self.evt_location_combo.findData(evt["location_id"])
        if idx >= 0:
            self.evt_location_combo.setCurrentIndex(idx)

    def _clear_event_form(self):
        self.evt_title_edit.clear()
        self.evt_type_edit.clear()
        self.evt_date_edit.clear()
        self.evt_desc_edit.clear()
        self.evt_notes_edit.clear()
        self._refresh_event_location_combo()

    def _reload_events(self, select_id=None):
        self.event_list.blockSignals(True)
        self.event_list.clear()
        if self.current_project_id is not None:
            for evt in self.db.list_events(self.current_project_id):
                label = evt["title"]
                if evt["date_label"]:
                    label = f"{evt['date_label']}  {evt['title']}"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, evt["id"])
                self.event_list.addItem(item)
                if select_id is not None and evt["id"] == select_id:
                    item.setSelected(True)
        self.event_list.blockSignals(False)
        if select_id is not None:
            self._on_event_selected()

    # ------------------------------------------------------------------
    # Creatures tab
    # ------------------------------------------------------------------
    def _build_creatures_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Bestiary"))
        self.creature_list = QListWidget()
        self.creature_list.itemSelectionChanged.connect(self._on_creature_selected)
        left_layout.addWidget(self.creature_list, 1)

        c_buttons = QHBoxLayout()
        add_c_btn = QPushButton("New")
        add_c_btn.clicked.connect(self._new_creature)
        del_c_btn = QPushButton("Delete")
        del_c_btn.clicked.connect(self._delete_creature)
        c_buttons.addWidget(add_c_btn)
        c_buttons.addWidget(del_c_btn)
        left_layout.addLayout(c_buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.crt_name_edit = QLineEdit()
        self.crt_type_edit = QLineEdit()
        self.crt_type_edit.setPlaceholderText("Dragon, Undead, Fey, Construct…")
        self.crt_habitat_edit = QLineEdit()
        self.crt_size_edit = QLineEdit()
        self.crt_size_edit.setPlaceholderText("Tiny / Small / Medium / Large / Colossal")
        self.crt_diet_edit = QLineEdit()
        form.addRow("Name:", self.crt_name_edit)
        form.addRow("Type:", self.crt_type_edit)
        form.addRow("Habitat:", self.crt_habitat_edit)
        form.addRow("Size:", self.crt_size_edit)
        form.addRow("Diet:", self.crt_diet_edit)
        right_layout.addLayout(form)

        tabs_inner = QTabWidget()

        behaviour_w = QWidget()
        bl = QVBoxLayout(behaviour_w)
        self.crt_behaviour_edit = QTextEdit()
        self.crt_behaviour_edit.setPlaceholderText("Social patterns, aggression, hunting tactics…")
        bl.addWidget(self.crt_behaviour_edit)
        tabs_inner.addTab(behaviour_w, "Behaviour")

        abilities_w = QWidget()
        al = QVBoxLayout(abilities_w)
        self.crt_abilities_edit = QTextEdit()
        self.crt_abilities_edit.setPlaceholderText("Special powers, resistances, senses…")
        al.addWidget(self.crt_abilities_edit)
        tabs_inner.addTab(abilities_w, "Abilities")

        weak_w = QWidget()
        wl = QVBoxLayout(weak_w)
        self.crt_weaknesses_edit = QTextEdit()
        self.crt_weaknesses_edit.setPlaceholderText("Vulnerabilities, banes, counter-measures…")
        wl.addWidget(self.crt_weaknesses_edit)
        tabs_inner.addTab(weak_w, "Weaknesses")

        lore_w = QWidget()
        ll = QVBoxLayout(lore_w)
        self.crt_lore_edit = QTextEdit()
        self.crt_lore_edit.setPlaceholderText("Origin myths, cultural significance, historical encounters…")
        ll.addWidget(self.crt_lore_edit)
        tabs_inner.addTab(lore_w, "Lore")

        notes_w = QWidget()
        nl = QVBoxLayout(notes_w)
        self.crt_notes_edit = QTextEdit()
        self.crt_notes_edit.setPlaceholderText("DM/Author notes, variants, stat blocks…")
        nl.addWidget(self.crt_notes_edit)
        tabs_inner.addTab(notes_w, "Notes")

        right_layout.addWidget(tabs_inner, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        save_c_btn = QPushButton("Save Creature")
        save_c_btn.setObjectName("accent")
        save_c_btn.clicked.connect(self._save_creature)
        btn_row.addWidget(save_c_btn)
        right_layout.addLayout(btn_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        return widget

    def _new_creature(self):
        if not self._require_project():
            return
        name, ok = QInputDialog.getText(self, "New Creature", "Creature name:")
        if not ok or not name.strip():
            return
        crt_id = self.db.create_creature(self.current_project_id, name)
        self._reload_creatures(select_id=crt_id)
        self.statusBar().showMessage(f"Creature '{name.strip()}' created")

    def _delete_creature(self):
        if self.current_creature_id is None:
            return
        crt = self.db.get_creature(self.current_creature_id)
        confirm = QMessageBox.question(
            self, "Delete Creature", f"Delete '{crt['name']}'?"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_creature(self.current_creature_id)
            self.current_creature_id = None
            self._reload_creatures()
            self._clear_creature_form()

    def _save_creature(self):
        if self.current_creature_id is None:
            QMessageBox.information(self, APP_TITLE, "Select or create a creature first.")
            return
        name = self.crt_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, APP_TITLE, "Creature name cannot be empty.")
            return
        self.db.update_creature(
            self.current_creature_id, name,
            self.crt_type_edit.text(),
            self.crt_habitat_edit.text(),
            self.crt_size_edit.text(),
            self.crt_diet_edit.text(),
            self.crt_behaviour_edit.toPlainText(),
            self.crt_abilities_edit.toPlainText(),
            self.crt_weaknesses_edit.toPlainText(),
            self.crt_lore_edit.toPlainText(),
            self.crt_notes_edit.toPlainText(),
        )
        self._reload_creatures(select_id=self.current_creature_id)
        self.statusBar().showMessage(f"Saved creature '{name}'")

    def _on_creature_selected(self):
        items = self.creature_list.selectedItems()
        if not items:
            return
        crt_id = items[0].data(Qt.ItemDataRole.UserRole)
        self.current_creature_id = crt_id
        crt = self.db.get_creature(crt_id)
        if crt is None:
            return
        self.crt_name_edit.setText(crt["name"])
        self.crt_type_edit.setText(crt["creature_type"])
        self.crt_habitat_edit.setText(crt["habitat"])
        self.crt_size_edit.setText(crt["size"])
        self.crt_diet_edit.setText(crt["diet"])
        self.crt_behaviour_edit.setPlainText(crt["behaviour"])
        self.crt_abilities_edit.setPlainText(crt["abilities"])
        self.crt_weaknesses_edit.setPlainText(crt["weaknesses"])
        self.crt_lore_edit.setPlainText(crt["lore"])
        self.crt_notes_edit.setPlainText(crt["notes"])

    def _clear_creature_form(self):
        for edit in (self.crt_name_edit, self.crt_type_edit, self.crt_habitat_edit,
                     self.crt_size_edit, self.crt_diet_edit):
            edit.clear()
        for tedit in (self.crt_behaviour_edit, self.crt_abilities_edit,
                      self.crt_weaknesses_edit, self.crt_lore_edit, self.crt_notes_edit):
            tedit.clear()

    def _reload_creatures(self, select_id=None):
        self.creature_list.blockSignals(True)
        self.creature_list.clear()
        if self.current_project_id is not None:
            for crt in self.db.list_creatures(self.current_project_id):
                item = QListWidgetItem(crt["name"])
                item.setData(Qt.ItemDataRole.UserRole, crt["id"])
                self.creature_list.addItem(item)
                if select_id is not None and crt["id"] == select_id:
                    item.setSelected(True)
        self.creature_list.blockSignals(False)
        if select_id is not None:
            self._on_creature_selected()

    # ------------------------------------------------------------------
    # Magic Systems tab
    # ------------------------------------------------------------------
    def _build_magic_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Magic Systems"))
        self.magic_list = QListWidget()
        self.magic_list.itemSelectionChanged.connect(self._on_magic_selected)
        left_layout.addWidget(self.magic_list, 1)

        m_buttons = QHBoxLayout()
        add_m_btn = QPushButton("New")
        add_m_btn.clicked.connect(self._new_magic)
        del_m_btn = QPushButton("Delete")
        del_m_btn.clicked.connect(self._delete_magic)
        m_buttons.addWidget(add_m_btn)
        m_buttons.addWidget(del_m_btn)
        left_layout.addLayout(m_buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.magic_name_edit = QLineEdit()
        self.magic_class_edit = QLineEdit()
        self.magic_class_edit.setPlaceholderText("Elemental, Rune, Psionics, Blood…")
        self.magic_source_edit = QLineEdit()
        self.magic_source_edit.setPlaceholderText("Ley lines, deity, emotion, study…")
        self.magic_cost_edit = QLineEdit()
        self.magic_cost_edit.setPlaceholderText("Stamina, lifespan, sanity…")
        form.addRow("Name:", self.magic_name_edit)
        form.addRow("Classification:", self.magic_class_edit)
        form.addRow("Source:", self.magic_source_edit)
        form.addRow("Cost:", self.magic_cost_edit)
        right_layout.addLayout(form)

        inner_tabs = QTabWidget()

        desc_w = QWidget()
        dl = QVBoxLayout(desc_w)
        self.magic_desc_edit = QTextEdit()
        self.magic_desc_edit.setPlaceholderText("Overview: how magic works in your world…")
        dl.addWidget(self.magic_desc_edit)
        inner_tabs.addTab(desc_w, "Description")

        rules_w = QWidget()
        rl = QVBoxLayout(rules_w)
        self.magic_rules_edit = QTextEdit()
        self.magic_rules_edit.setPlaceholderText("Mechanics, casting procedures, interactions…")
        rl.addWidget(self.magic_rules_edit)
        inner_tabs.addTab(rules_w, "Rules")

        lim_w = QWidget()
        ll = QVBoxLayout(lim_w)
        self.magic_limits_edit = QTextEdit()
        self.magic_limits_edit.setPlaceholderText("What can't it do? Countermeasures, forbidden magic…")
        ll.addWidget(self.magic_limits_edit)
        inner_tabs.addTab(lim_w, "Limitations")

        ab_w = QWidget()
        al = QVBoxLayout(ab_w)
        al.addWidget(QLabel("Abilities / Spells / Powers"))
        self.magic_ability_table = QTableWidget(0, 4)
        self.magic_ability_table.setHorizontalHeaderLabels(
            ["Name", "Tier", "Description", "Notes"]
        )
        self.magic_ability_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.magic_ability_table.setAlternatingRowColors(True)
        al.addWidget(self.magic_ability_table, 1)
        ab_btns = QHBoxLayout()
        add_ab_btn = QPushButton("Add Ability")
        add_ab_btn.clicked.connect(self._add_magic_ability_row)
        rm_ab_btn = QPushButton("Remove")
        rm_ab_btn.clicked.connect(self._remove_magic_ability_row)
        ab_btns.addWidget(add_ab_btn)
        ab_btns.addWidget(rm_ab_btn)
        ab_btns.addStretch(1)
        al.addLayout(ab_btns)
        inner_tabs.addTab(ab_w, "Abilities")

        right_layout.addWidget(inner_tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        save_m_btn = QPushButton("Save Magic System")
        save_m_btn.setObjectName("accent")
        save_m_btn.clicked.connect(self._save_magic)
        btn_row.addWidget(save_m_btn)
        right_layout.addLayout(btn_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        return widget

    def _new_magic(self):
        if not self._require_project():
            return
        name, ok = QInputDialog.getText(self, "New Magic System", "System name:")
        if not ok or not name.strip():
            return
        mid = self.db.create_magic_system(self.current_project_id, name)
        self._reload_magic_systems(select_id=mid)
        self.statusBar().showMessage(f"Magic system '{name.strip()}' created")

    def _delete_magic(self):
        if self.current_magic_id is None:
            return
        ms = self.db.get_magic_system(self.current_magic_id)
        confirm = QMessageBox.question(
            self, "Delete Magic System", f"Delete '{ms['name']}'?"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_magic_system(self.current_magic_id)
            self.current_magic_id = None
            self._reload_magic_systems()
            self._clear_magic_form()

    def _save_magic(self):
        if self.current_magic_id is None:
            QMessageBox.information(self, APP_TITLE, "Select or create a magic system first.")
            return
        name = self.magic_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, APP_TITLE, "System name cannot be empty.")
            return
        self.db.update_magic_system(
            self.current_magic_id, name,
            self.magic_class_edit.text(),
            self.magic_desc_edit.toPlainText(),
            self.magic_rules_edit.toPlainText(),
            self.magic_source_edit.text(),
            self.magic_limits_edit.toPlainText(),
            self.magic_cost_edit.text(),
        )
        abilities = []
        for row in range(self.magic_ability_table.rowCount()):
            vals = []
            for col in range(4):
                item = self.magic_ability_table.item(row, col)
                vals.append(item.text() if item else "")
            # order in table: Name, Tier, Description, Notes
            abilities.append((vals[0], vals[2], vals[1], vals[3]))
        self.db.replace_magic_abilities(self.current_magic_id, abilities)
        self._reload_magic_systems(select_id=self.current_magic_id)
        self.statusBar().showMessage(f"Saved magic system '{name}'")

    def _on_magic_selected(self):
        items = self.magic_list.selectedItems()
        if not items:
            return
        mid = items[0].data(Qt.ItemDataRole.UserRole)
        self.current_magic_id = mid
        ms = self.db.get_magic_system(mid)
        if ms is None:
            return
        self.magic_name_edit.setText(ms["name"])
        self.magic_class_edit.setText(ms["classification"])
        self.magic_source_edit.setText(ms["source"])
        self.magic_cost_edit.setText(ms["cost"])
        self.magic_desc_edit.setPlainText(ms["description"])
        self.magic_rules_edit.setPlainText(ms["rules"])
        self.magic_limits_edit.setPlainText(ms["limitations"])
        self.magic_ability_table.setRowCount(0)
        for ab in self.db.list_magic_abilities(mid):
            row = self.magic_ability_table.rowCount()
            self.magic_ability_table.insertRow(row)
            self.magic_ability_table.setItem(row, 0, QTableWidgetItem(ab["name"]))
            self.magic_ability_table.setItem(row, 1, QTableWidgetItem(ab["tier"]))
            self.magic_ability_table.setItem(row, 2, QTableWidgetItem(ab["description"]))
            self.magic_ability_table.setItem(row, 3, QTableWidgetItem(ab["notes"]))

    def _add_magic_ability_row(self):
        row = self.magic_ability_table.rowCount()
        self.magic_ability_table.insertRow(row)
        for col in range(4):
            self.magic_ability_table.setItem(row, col, QTableWidgetItem(""))

    def _remove_magic_ability_row(self):
        row = self.magic_ability_table.currentRow()
        if row >= 0:
            self.magic_ability_table.removeRow(row)

    def _clear_magic_form(self):
        self.magic_name_edit.clear()
        self.magic_class_edit.clear()
        self.magic_source_edit.clear()
        self.magic_cost_edit.clear()
        self.magic_desc_edit.clear()
        self.magic_rules_edit.clear()
        self.magic_limits_edit.clear()
        self.magic_ability_table.setRowCount(0)

    def _reload_magic_systems(self, select_id=None):
        self.magic_list.blockSignals(True)
        self.magic_list.clear()
        if self.current_project_id is not None:
            for ms in self.db.list_magic_systems(self.current_project_id):
                item = QListWidgetItem(ms["name"])
                item.setData(Qt.ItemDataRole.UserRole, ms["id"])
                self.magic_list.addItem(item)
                if select_id is not None and ms["id"] == select_id:
                    item.setSelected(True)
        self.magic_list.blockSignals(False)
        if select_id is not None:
            self._on_magic_selected()

    # ------------------------------------------------------------------
    # Religions tab
    # ------------------------------------------------------------------
    def _build_religions_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Religions & Faiths"))
        self.religion_list = QListWidget()
        self.religion_list.itemSelectionChanged.connect(self._on_religion_selected)
        left_layout.addWidget(self.religion_list, 1)

        r_buttons = QHBoxLayout()
        add_r_btn = QPushButton("New")
        add_r_btn.clicked.connect(self._new_religion)
        del_r_btn = QPushButton("Delete")
        del_r_btn.clicked.connect(self._delete_religion)
        r_buttons.addWidget(add_r_btn)
        r_buttons.addWidget(del_r_btn)
        left_layout.addLayout(r_buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.rel_name_edit = QLineEdit()
        self.rel_pantheon_edit = QLineEdit()
        self.rel_pantheon_edit.setPlaceholderText("Monotheistic, Polytheistic, Animist…")
        self.rel_holy_texts_edit = QLineEdit()
        form.addRow("Name:", self.rel_name_edit)
        form.addRow("Pantheon Type:", self.rel_pantheon_edit)
        form.addRow("Holy Texts:", self.rel_holy_texts_edit)
        right_layout.addLayout(form)

        inner_tabs = QTabWidget()

        desc_w = QWidget()
        dl = QVBoxLayout(desc_w)
        self.rel_desc_edit = QTextEdit()
        self.rel_desc_edit.setPlaceholderText("Overview, history, spread across the world…")
        dl.addWidget(self.rel_desc_edit)
        inner_tabs.addTab(desc_w, "Description")

        beliefs_w = QWidget()
        bl = QVBoxLayout(beliefs_w)
        self.rel_beliefs_edit = QTextEdit()
        self.rel_beliefs_edit.setPlaceholderText("Core tenets, cosmology, creation myths…")
        bl.addWidget(self.rel_beliefs_edit)
        inner_tabs.addTab(beliefs_w, "Beliefs")

        practices_w = QWidget()
        pl = QVBoxLayout(practices_w)
        self.rel_practices_edit = QTextEdit()
        self.rel_practices_edit.setPlaceholderText("Rituals, holy days, clergy, temples…")
        pl.addWidget(self.rel_practices_edit)
        inner_tabs.addTab(practices_w, "Practices")

        afterlife_w = QWidget()
        al = QVBoxLayout(afterlife_w)
        self.rel_afterlife_edit = QTextEdit()
        self.rel_afterlife_edit.setPlaceholderText("Heaven, reincarnation, oblivion, undeath…")
        al.addWidget(self.rel_afterlife_edit)
        inner_tabs.addTab(afterlife_w, "Afterlife")

        deities_w = QWidget()
        dyl = QVBoxLayout(deities_w)
        dyl.addWidget(QLabel("Deities / Spirits / Powers"))
        self.deity_table = QTableWidget(0, 5)
        self.deity_table.setHorizontalHeaderLabels(
            ["Name", "Domain", "Alignment", "Description", "Notes"]
        )
        self.deity_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.deity_table.setAlternatingRowColors(True)
        dyl.addWidget(self.deity_table, 1)
        deity_btns = QHBoxLayout()
        add_deity_btn = QPushButton("Add Deity")
        add_deity_btn.clicked.connect(self._add_deity_row)
        rm_deity_btn = QPushButton("Remove")
        rm_deity_btn.clicked.connect(self._remove_deity_row)
        deity_btns.addWidget(add_deity_btn)
        deity_btns.addWidget(rm_deity_btn)
        deity_btns.addStretch(1)
        dyl.addLayout(deity_btns)
        inner_tabs.addTab(deities_w, "Deities")

        right_layout.addWidget(inner_tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        save_r_btn = QPushButton("Save Religion")
        save_r_btn.setObjectName("accent")
        save_r_btn.clicked.connect(self._save_religion)
        btn_row.addWidget(save_r_btn)
        right_layout.addLayout(btn_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        return widget

    def _new_religion(self):
        if not self._require_project():
            return
        name, ok = QInputDialog.getText(self, "New Religion", "Religion name:")
        if not ok or not name.strip():
            return
        rid = self.db.create_religion(self.current_project_id, name)
        self._reload_religions(select_id=rid)
        self.statusBar().showMessage(f"Religion '{name.strip()}' created")

    def _delete_religion(self):
        if self.current_religion_id is None:
            return
        rel = self.db.get_religion(self.current_religion_id)
        confirm = QMessageBox.question(
            self, "Delete Religion", f"Delete '{rel['name']}'?"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_religion(self.current_religion_id)
            self.current_religion_id = None
            self._reload_religions()
            self._clear_religion_form()

    def _save_religion(self):
        if self.current_religion_id is None:
            QMessageBox.information(self, APP_TITLE, "Select or create a religion first.")
            return
        name = self.rel_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, APP_TITLE, "Religion name cannot be empty.")
            return
        self.db.update_religion(
            self.current_religion_id, name,
            self.rel_pantheon_edit.text(),
            self.rel_desc_edit.toPlainText(),
            self.rel_beliefs_edit.toPlainText(),
            self.rel_practices_edit.toPlainText(),
            self.rel_holy_texts_edit.text(),
            self.rel_afterlife_edit.toPlainText(),
        )
        deities = []
        for row in range(self.deity_table.rowCount()):
            vals = []
            for col in range(5):
                item = self.deity_table.item(row, col)
                vals.append(item.text() if item else "")
            # Name, Domain, Alignment, Description, Notes
            deities.append((vals[0], vals[1], vals[3], vals[2], vals[4]))
        self.db.replace_religion_deities(self.current_religion_id, deities)
        self._reload_religions(select_id=self.current_religion_id)
        self.statusBar().showMessage(f"Saved religion '{name}'")

    def _on_religion_selected(self):
        items = self.religion_list.selectedItems()
        if not items:
            return
        rid = items[0].data(Qt.ItemDataRole.UserRole)
        self.current_religion_id = rid
        rel = self.db.get_religion(rid)
        if rel is None:
            return
        self.rel_name_edit.setText(rel["name"])
        self.rel_pantheon_edit.setText(rel["pantheon_type"])
        self.rel_holy_texts_edit.setText(rel["holy_texts"])
        self.rel_desc_edit.setPlainText(rel["description"])
        self.rel_beliefs_edit.setPlainText(rel["beliefs"])
        self.rel_practices_edit.setPlainText(rel["practices"])
        self.rel_afterlife_edit.setPlainText(rel["afterlife_views"])
        self.deity_table.setRowCount(0)
        for d in self.db.list_religion_deities(rid):
            row = self.deity_table.rowCount()
            self.deity_table.insertRow(row)
            self.deity_table.setItem(row, 0, QTableWidgetItem(d["name"]))
            self.deity_table.setItem(row, 1, QTableWidgetItem(d["domain"]))
            self.deity_table.setItem(row, 2, QTableWidgetItem(d["alignment"]))
            self.deity_table.setItem(row, 3, QTableWidgetItem(d["description"]))
            self.deity_table.setItem(row, 4, QTableWidgetItem(d["notes"]))

    def _add_deity_row(self):
        row = self.deity_table.rowCount()
        self.deity_table.insertRow(row)
        for col in range(5):
            self.deity_table.setItem(row, col, QTableWidgetItem(""))

    def _remove_deity_row(self):
        row = self.deity_table.currentRow()
        if row >= 0:
            self.deity_table.removeRow(row)

    def _clear_religion_form(self):
        self.rel_name_edit.clear()
        self.rel_pantheon_edit.clear()
        self.rel_holy_texts_edit.clear()
        self.rel_desc_edit.clear()
        self.rel_beliefs_edit.clear()
        self.rel_practices_edit.clear()
        self.rel_afterlife_edit.clear()
        self.deity_table.setRowCount(0)

    def _reload_religions(self, select_id=None):
        self.religion_list.blockSignals(True)
        self.religion_list.clear()
        if self.current_project_id is not None:
            for rel in self.db.list_religions(self.current_project_id):
                item = QListWidgetItem(rel["name"])
                item.setData(Qt.ItemDataRole.UserRole, rel["id"])
                self.religion_list.addItem(item)
                if select_id is not None and rel["id"] == select_id:
                    item.setSelected(True)
        self.religion_list.blockSignals(False)
        if select_id is not None:
            self._on_religion_selected()

    # ------------------------------------------------------------------
    # Manuscripts tab
    # ------------------------------------------------------------------
    def _build_manuscripts_tab(self):
        widget = QWidget()
        root = QVBoxLayout(widget)

        header = QLabel("Manuscripts")
        header.setObjectName("sectionTitle")
        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left panel: manuscript list ───────────────────────────────
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)

        ms_btn_row = QHBoxLayout()
        new_ms_btn = QPushButton("+ Manuscript")
        new_ms_btn.clicked.connect(self._new_manuscript)
        del_ms_btn = QPushButton("Delete")
        del_ms_btn.clicked.connect(self._delete_manuscript)
        ms_btn_row.addWidget(new_ms_btn)
        ms_btn_row.addWidget(del_ms_btn)
        ms_btn_row.addStretch(1)
        lv.addLayout(ms_btn_row)

        self.ms_list = QListWidget()
        self.ms_list.currentItemChanged.connect(self._on_manuscript_selected)
        lv.addWidget(self.ms_list, 1)

        self.ms_word_count_label = QLabel("")
        self.ms_word_count_label.setObjectName("statusHint")
        lv.addWidget(self.ms_word_count_label)

        splitter.addWidget(left)

        # ── Right panel: manuscript detail + chapter editor ───────────
        right = QTabWidget()
        right.setDocumentMode(False)
        self.ms_subtabs = right

        # ── Overview sub-tab: manuscript metadata ─────────────────────
        overview_page = QWidget()
        rv = QVBoxLayout(overview_page)
        rv.setContentsMargins(8, 8, 8, 8)

        ms_form = QFormLayout()
        self.ms_title_edit = QLineEdit()
        self.ms_genre_edit = QLineEdit()
        self.ms_status_combo = QComboBox()
        self.ms_status_combo.addItems(["Draft", "In Progress", "Revision", "Complete"])
        self.ms_synopsis_edit = QTextEdit()
        self.ms_synopsis_edit.setMinimumHeight(160)
        ms_form.addRow("Title:", self.ms_title_edit)
        ms_form.addRow("Genre:", self.ms_genre_edit)
        ms_form.addRow("Status:", self.ms_status_combo)
        ms_form.addRow("Synopsis:", self.ms_synopsis_edit)
        rv.addLayout(ms_form)

        ms_save_btn = QPushButton("Save Manuscript")
        ms_save_btn.setObjectName("accent")
        ms_save_btn.clicked.connect(self._save_manuscript)
        rv.addWidget(ms_save_btn)
        rv.addStretch(1)
        right.addTab(overview_page, "Overview")

        # ── Chapters sub-tab ──────────────────────────────────────────
        chapters_page = QWidget()
        cv = QVBoxLayout(chapters_page)
        cv.setContentsMargins(8, 8, 8, 8)

        ch_header_row = QHBoxLayout()
        ch_header_row.addWidget(QLabel("Chapters"))
        new_ch_btn = QPushButton("+ Chapter")
        new_ch_btn.clicked.connect(self._new_chapter)
        del_ch_btn = QPushButton("Delete Chapter")
        del_ch_btn.clicked.connect(self._delete_chapter)
        ch_header_row.addStretch(1)
        ch_header_row.addWidget(new_ch_btn)
        ch_header_row.addWidget(del_ch_btn)
        cv.addLayout(ch_header_row)

        ch_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.ch_list = QListWidget()
        self.ch_list.setMaximumWidth(200)
        self.ch_list.currentItemChanged.connect(self._on_chapter_selected)
        ch_splitter.addWidget(self.ch_list)

        ch_right = QWidget()
        chv = QVBoxLayout(ch_right)
        chv.setContentsMargins(4, 0, 0, 0)
        ch_form = QFormLayout()
        self.ch_title_edit = QLineEdit()
        self.ch_status_combo = QComboBox()
        self.ch_status_combo.addItems(["Draft", "In Progress", "Revision", "Complete"])
        ch_form.addRow("Chapter title:", self.ch_title_edit)
        ch_form.addRow("Status:", self.ch_status_combo)
        chv.addLayout(ch_form)

        chv.addWidget(QLabel("Body:"))
        self.ch_body_edit = QTextEdit()
        chv.addWidget(self.ch_body_edit, 1)

        chv.addWidget(QLabel("Notes:"))
        self.ch_notes_edit = QTextEdit()
        self.ch_notes_edit.setMaximumHeight(70)
        chv.addWidget(self.ch_notes_edit)

        ch_save_btn = QPushButton("Save Chapter")
        ch_save_btn.setObjectName("accent")
        ch_save_btn.clicked.connect(self._save_chapter)
        chv.addWidget(ch_save_btn)

        ch_splitter.addWidget(ch_right)
        ch_splitter.setStretchFactor(1, 1)
        cv.addWidget(ch_splitter, 1)
        right.addTab(chapters_page, "Chapters")

        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 900])

        root.addWidget(splitter, 1)
        return widget

    # ── Manuscript helpers ─────────────────────────────────────────────────
    def _new_manuscript(self):
        if not self._require_project():
            return
        title, ok = QInputDialog.getText(self, "New Manuscript", "Title:")
        if not ok or not title.strip():
            return
        mid = self.db.create_manuscript(self.current_project_id, title.strip())
        self._reload_manuscripts(select_id=mid)

    def _delete_manuscript(self):
        if not self.current_manuscript_id:
            return
        ms = self.db.get_manuscript(self.current_manuscript_id)
        reply = QMessageBox.question(
            self, "Delete Manuscript",
            f"Delete '{ms['title']}' and all its chapters?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_manuscript(self.current_manuscript_id)
        self.current_manuscript_id = None
        self.current_chapter_id = None
        self._reload_manuscripts()

    def _save_manuscript(self):
        if not self.current_manuscript_id:
            return
        self.db.update_manuscript(
            self.current_manuscript_id,
            self.ms_title_edit.text(),
            self.ms_genre_edit.text(),
            self.ms_synopsis_edit.toPlainText(),
            self.ms_status_combo.currentText(),
        )
        self._reload_manuscripts(select_id=self.current_manuscript_id)
        self.statusBar().showMessage("Manuscript saved")

    def _on_manuscript_selected(self, current, _prev):
        if not current:
            self.current_manuscript_id = None
            return
        mid = current.data(Qt.ItemDataRole.UserRole)
        self.current_manuscript_id = mid
        ms = self.db.get_manuscript(mid)
        self.ms_title_edit.setText(ms["title"])
        self.ms_genre_edit.setText(ms["genre"])
        self.ms_synopsis_edit.setPlainText(ms["synopsis"])
        idx = self.ms_status_combo.findText(ms["status"])
        self.ms_status_combo.setCurrentIndex(max(0, idx))
        wc = ms.get("word_count", 0)
        self.ms_word_count_label.setText(f"{wc:,} words")
        self._reload_chapters()

    def _reload_manuscripts(self, select_id=None):
        self.ms_list.blockSignals(True)
        self.ms_list.clear()
        if self.current_project_id:
            for ms in self.db.list_manuscripts(self.current_project_id):
                item = QListWidgetItem(ms["title"])
                item.setData(Qt.ItemDataRole.UserRole, ms["id"])
                self.ms_list.addItem(item)
                if ms["id"] == select_id:
                    self.ms_list.setCurrentItem(item)
        self.ms_list.blockSignals(False)
        if select_id:
            cur = self.ms_list.currentItem()
            if cur:
                self._on_manuscript_selected(cur, None)
        else:
            self.current_manuscript_id = None
            self.ch_list.clear()
            self.ms_word_count_label.setText("")

    # ── Chapter helpers ────────────────────────────────────────────────────
    def _new_chapter(self):
        if not self.current_manuscript_id:
            QMessageBox.information(self, APP_TITLE, "Select a manuscript first.")
            return
        title, ok = QInputDialog.getText(self, "New Chapter", "Chapter title (optional):")
        if not ok:
            return
        cid = self.db.add_chapter(self.current_manuscript_id, title.strip())
        self._reload_chapters(select_id=cid)

    def _delete_chapter(self):
        if not self.current_chapter_id:
            return
        reply = QMessageBox.question(
            self, "Delete Chapter", "Delete this chapter?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_chapter(self.current_chapter_id)
        self.current_chapter_id = None
        self._reload_chapters()
        # refresh word count
        if self.current_manuscript_id:
            ms = self.db.get_manuscript(self.current_manuscript_id)
            self.ms_word_count_label.setText(f"{ms.get('word_count', 0):,} words")

    def _save_chapter(self):
        if not self.current_chapter_id:
            return
        self.db.update_chapter(
            self.current_chapter_id,
            self.ch_title_edit.text(),
            self.ch_body_edit.toPlainText(),
            self.ch_notes_edit.toPlainText(),
            self.ch_status_combo.currentText(),
        )
        self._reload_chapters(select_id=self.current_chapter_id)
        if self.current_manuscript_id:
            ms = self.db.get_manuscript(self.current_manuscript_id)
            self.ms_word_count_label.setText(f"{ms.get('word_count', 0):,} words")
        self.statusBar().showMessage("Chapter saved")

    def _on_chapter_selected(self, current, _prev):
        if not current:
            self.current_chapter_id = None
            return
        cid = current.data(Qt.ItemDataRole.UserRole)
        self.current_chapter_id = cid
        ch = self.db.get_chapter(cid)
        self.ch_title_edit.setText(ch["title"])
        self.ch_body_edit.setPlainText(ch["body"])
        self.ch_notes_edit.setPlainText(ch["notes"])
        idx = self.ch_status_combo.findText(ch["status"])
        self.ch_status_combo.setCurrentIndex(max(0, idx))

    def _reload_chapters(self, select_id=None):
        self.ch_list.blockSignals(True)
        self.ch_list.clear()
        if self.current_manuscript_id:
            for ch in self.db.list_chapters(self.current_manuscript_id):
                label = f"Ch {ch['chapter_number']}"
                if ch["title"]:
                    label += f": {ch['title']}"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, ch["id"])
                self.ch_list.addItem(item)
                if ch["id"] == select_id:
                    self.ch_list.setCurrentItem(item)
        self.ch_list.blockSignals(False)
        if select_id:
            cur = self.ch_list.currentItem()
            if cur:
                self._on_chapter_selected(cur, None)
        else:
            self.current_chapter_id = None


      

    def _cloud_upload_file(self):
        """Upload a selected local file to the signed-in user's Supabase bucket."""
        if not self._supabase_access_token or not self._supabase_user_id:
            QMessageBox.information(self, APP_TITLE, "Sign in before uploading cloud files.")
            return
        local_path, _ = QFileDialog.getOpenFileName(self, "Choose file to upload to Supabase Storage")
        if not local_path:
            return
        object_key, ok = QInputDialog.getText(
            self, "Cloud object name", "File path in bucket:",
            text=os.path.basename(local_path)
        )
        if not ok or not object_key.strip():
            return
        try:
            from storage_client import upload_project_file, DEFAULT_BUCKET
            user_prefix = (self._supabase_user_id.strip("/") + "/") if self._supabase_user_id else ""
            safe_object_key = user_prefix + object_key.strip("/")
            upload_project_file(local_path, safe_object_key, self._supabase_access_token, DEFAULT_BUCKET)
            QMessageBox.information(self, "Upload complete", f"Uploaded {os.path.basename(local_path)} to {DEFAULT_BUCKET}.")
        except Exception as exc:
            QMessageBox.critical(self, "Cloud upload failed", str(exc))

    def _cloud_download_file(self):
        """Open the cloud browser so users can see and select their files."""
        if not self._supabase_access_token or not self._supabase_user_id:
            QMessageBox.information(self, APP_TITLE, "Sign in before browsing cloud files.")
            return
        try:
            from storage_client import DEFAULT_BUCKET
            dialog = CloudFilesDialog(self, self._supabase_access_token, DEFAULT_BUCKET, self._supabase_user_id or "")
            dialog.exec()
        except Exception as exc:
            QMessageBox.critical(self, "Cloud files", str(exc))

        # ------------------------------------------------------------------
    # Font Studio tab
    # ------------------------------------------------------------------
    def _build_font_studio_tab(self):
        outer = QWidget()
        layout = QVBoxLayout(outer)
        layout.setSpacing(10)

        header = QLabel("Font Studio")
        header.setObjectName("sectionTitle")
        layout.addWidget(header)


        # ── Font name ──────────────────────────────────────────────────
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Font name:"))
        self.font_name_edit = QLineEdit()
        self.font_name_edit.setPlaceholderText("e.g. MyCustomFont")
        self.font_name_edit.setText("MyCustomFont")
        name_row.addWidget(self.font_name_edit, 1)
        layout.addLayout(name_row)

        # ── PNG picker ─────────────────────────────────────────────────
        png_group = QGroupBox("Glyph PNGs")
        png_layout = QVBoxLayout(png_group)

        pick_row = QHBoxLayout()
        self.font_png_folder_label = QLabel("No folder selected")
        self.font_png_folder_label.setObjectName("statusHint")
        pick_row.addWidget(self.font_png_folder_label, 1)

        pick_folder_btn = QPushButton("Choose PNG Folder…")
        pick_folder_btn.clicked.connect(self._font_pick_folder)
        pick_row.addWidget(pick_folder_btn)

        pick_files_btn = QPushButton("Pick Individual PNGs…")
        pick_files_btn.clicked.connect(self._font_pick_files)
        pick_row.addWidget(pick_files_btn)

        clear_btn = QPushButton("Clear List")
        clear_btn.clicked.connect(self._font_clear_pngs)
        pick_row.addWidget(clear_btn)
        png_layout.addLayout(pick_row)

        self.font_png_list = QListWidget()
        self.font_png_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self.font_png_list.setAlternatingRowColors(True)
        self.font_png_list.setMaximumHeight(180)
        png_layout.addWidget(self.font_png_list)

        remove_sel_btn = QPushButton("Remove Selected")
        remove_sel_btn.clicked.connect(self._font_remove_selected)
        png_layout.addWidget(remove_sel_btn)

        layout.addWidget(png_group)

        # ── Output folder ──────────────────────────────────────────────
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output folder:"))
        self.font_output_label = QLabel("Same as PNG folder")
        self.font_output_label.setObjectName("statusHint")
        out_row.addWidget(self.font_output_label, 1)
        pick_out_btn = QPushButton("Change…")
        pick_out_btn.clicked.connect(self._font_pick_output)
        out_row.addWidget(pick_out_btn)
        layout.addLayout(out_row)

        self._font_custom_output: str | None = None  # None = use png folder

        # ── Generate button ────────────────────────────────────────────
        gen_row = QHBoxLayout()
        gen_row.addStretch(1)
        self.font_gen_btn = QPushButton("Generate TTF")
        self.font_gen_btn.setObjectName("accent")
        self.font_gen_btn.setFixedWidth(140)
        self.font_gen_btn.clicked.connect(self._font_generate)
        gen_row.addWidget(self.font_gen_btn)

        bundle_btn = QPushButton("Generate & Bundle into Export")
        bundle_btn.setObjectName("accent")
        bundle_btn.clicked.connect(self._font_generate_and_bundle)
        gen_row.addWidget(bundle_btn)
        layout.addLayout(gen_row)

        # ── Status / result ────────────────────────────────────────────
        self.font_status_label = QLabel("")
        self.font_status_label.setObjectName("statusHint")
        self.font_status_label.setWordWrap(True)
        layout.addWidget(self.font_status_label)

        layout.addStretch(1)

        # Internal state
        self._font_png_paths: list[str] = []   # absolute paths chosen by user

        return outer

    # ── Font Studio helpers ────────────────────────────────────────────────

    def _font_pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select PNG Glyph Folder")
        if not folder:
            return
        import glob
        pngs = sorted(glob.glob(os.path.join(folder, "*.png")))
        if not pngs:
            QMessageBox.information(self, APP_TITLE, "No PNG files found in that folder.")
            return
        self._font_png_paths = pngs
        self.font_png_folder_label.setText(folder)
        self._font_refresh_list()
        self.font_status_label.setText(f"Loaded {len(pngs)} PNG(s) from folder.")

    def _font_pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Glyph PNG Files", "", "PNG Images (*.png)"
        )
        if not files:
            return
        # Deduplicate, preserving order
        existing = set(self._font_png_paths)
        for f in sorted(files):
            if f not in existing:
                self._font_png_paths.append(f)
                existing.add(f)
        self.font_png_folder_label.setText(f"{len(self._font_png_paths)} file(s) selected")
        self._font_refresh_list()

    def _font_clear_pngs(self):
        self._font_png_paths.clear()
        self.font_png_list.clear()
        self.font_png_folder_label.setText("No folder selected")
        self.font_status_label.setText("")

    def _font_remove_selected(self):
        selected = [item.text() for item in self.font_png_list.selectedItems()]
        self._font_png_paths = [p for p in self._font_png_paths
                                 if os.path.basename(p) not in selected]
        self._font_refresh_list()

    def _font_pick_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self._font_custom_output = folder
            self.font_output_label.setText(folder)

    def _font_refresh_list(self):
        self.font_png_list.clear()
        for p in self._font_png_paths:
            self.font_png_list.addItem(os.path.basename(p))

    def _font_resolve_output_dir(self) -> str:
        if self._font_custom_output:
            return self._font_custom_output
        if self._font_png_paths:
            return os.path.dirname(self._font_png_paths[0])
        return os.path.expanduser("~")

    def _font_run_generation(self) -> str:
        """Core logic: write PNGs to a temp folder then call FontStudioConverter."""
        font_name = self.font_name_edit.text().strip() or "MyCustomFont"

        if not self._font_png_paths:
            raise ValueError("No PNG files selected. Use 'Choose PNG Folder' or 'Pick Individual PNGs'.")

        # Write selected PNGs into a temporary sub-folder so FontStudioConverter
        # sees exactly the files the user chose.
        import tempfile, shutil as _shutil
        tmp_dir = tempfile.mkdtemp(prefix="storyforge_glyphs_")
        try:
            for p in self._font_png_paths:
                _shutil.copy2(p, tmp_dir)

            from font_studio import FontStudioConverter
            fsc = FontStudioConverter()
            out_dir = self._font_resolve_output_dir()
            ttf_path = fsc.create_ttf_from_pngs(
                png_folder=tmp_dir,
                output_name=font_name,
                output_dir=out_dir,
            )
        finally:
            _shutil.rmtree(tmp_dir, ignore_errors=True)

        return ttf_path

    def _font_generate(self):
        self.font_gen_btn.setEnabled(False)
        self.font_status_label.setText("Generating TTF…")
        QApplication.processEvents()
        try:
            ttf_path = self._font_run_generation()
            self.font_status_label.setText(f"✓ Font saved to: {ttf_path}")
            self.statusBar().showMessage(f"Font generated: {os.path.basename(ttf_path)}")
            QMessageBox.information(
                self, "Font Studio",
                f"TTF generated successfully!\n\n{ttf_path}\n\n"
                "You can now install it by double-clicking the file."
            )
        except Exception as exc:
            self.font_status_label.setText(f"⚠ {exc}")
            QMessageBox.critical(self, "Font Studio — Error", str(exc))
        finally:
            self.font_gen_btn.setEnabled(True)

    def _font_generate_and_bundle(self):
        """Generate the TTF and copy it into the current project's export folder."""
        if not self._require_project():
            return

        self.font_gen_btn.setEnabled(False)
        self.font_status_label.setText("Generating TTF…")
        QApplication.processEvents()
        try:
            ttf_path = self._font_run_generation()

            # Determine export folder (mirrors _export_workspace logic)
            project = self.db.get_project(self.current_project_id)
            slug = safe_slug(project["name"])

            target_dir = QFileDialog.getExistingDirectory(
                self, "Choose export destination to bundle font into"
            )
            if not target_dir:
                self.font_status_label.setText(f"✓ Font saved to: {ttf_path} (not bundled)")
                return

            bundle_dir = os.path.join(target_dir, f"{slug}_export")
            os.makedirs(bundle_dir, exist_ok=True)
            dest = shutil.copy2(ttf_path, bundle_dir)

            # Persist the font path on the project record (best-effort)
            try:
                if hasattr(self.db, "set_project_font_path"):
                    self.db.set_project_font_path(self.current_project_id, ttf_path)
            except Exception:
                pass  # DB might not support this yet — non-fatal

            self.font_status_label.setText(f"✓ Font bundled: {dest}")
            self.statusBar().showMessage(f"Font bundled into {bundle_dir}")
            QMessageBox.information(
                self, "Font Studio",
                f"TTF generated and bundled!\n\nFont file:\n  {ttf_path}\n\n"
                f"Bundled to:\n  {dest}"
            )
        except Exception as exc:
            self.font_status_label.setText(f"⚠ {exc}")
            QMessageBox.critical(self, "Font Studio — Error", str(exc))
        finally:
            self.font_gen_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Export Workspace
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Supabase account and project snapshot sync
    # ------------------------------------------------------------------
    def _supabase_request(self, path, method="GET", payload=None, token=None, prefer=None):
        base = SUPABASE_URL.rstrip("/")
        url = base + path
        headers = {
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Authorization": "Bearer " + (token or SUPABASE_PUBLISHABLE_KEY),
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Supabase returned HTTP {exc.code}: {detail[:700]}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Could not reach Supabase: {exc}") from exc

    def _cloud_account_dialog(self):
        if self._supabase_access_token:
            choice = QMessageBox.question(
                self, APP_TITLE,
                f"Signed in as {self._supabase_email}.\n\nSign out of this Story Forge account?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice == QMessageBox.StandardButton.Yes:
                try:
                    self._supabase_request("/auth/v1/logout", method="POST", token=self._supabase_access_token)
                except Exception:
                    pass  # Local sign-out should still work if the network is unavailable.
                self._supabase_access_token = None
                self._supabase_user_id = None
                self._supabase_email = None
                self.account_btn.setText("Story Forge Account: Sign In")
                self.statusBar().showMessage("Signed out. Local projects remain on this computer.")
            return

        dialog = AccountDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        email = dialog.email.text().strip()
        password = dialog.password.text()
        mode = dialog.mode.currentText()
        try:
            endpoint = "signup" if mode == "Create account" else "token?grant_type=password"
            result = self._supabase_request(
                "/auth/v1/" + endpoint, method="POST",
                payload={"email": email, "password": password}
            ) or {}
            if not result.get("access_token"):
                QMessageBox.information(
                    self, APP_TITLE,
                    "Supabase accepted the account request but did not issue a session. "
                    "Check your email for a confirmation link, then choose Sign in."
                )
                return
            user = result.get("user") or {}
            self._supabase_access_token = result["access_token"]
            self._supabase_user_id = user.get("id")
            self._supabase_email = user.get("email", email)
            self.account_btn.setText("Account: " + self._supabase_email)
            self.statusBar().showMessage("Signed in. Starting cloud sync…")
            self._cloud_sync_now()
        except Exception as exc:
            QMessageBox.critical(
                self, APP_TITLE,
                "Could not connect to your Story Forge account. Check your credentials "
                "and Supabase Authentication settings.\n\n" + str(exc)
            )

    def _cloud_auto_sync(self):
        if self._supabase_access_token and self.current_project_id is not None:
            self._cloud_sync_now(show_messages=False)

    def _cloud_sync_now(self, show_messages=True):
        if not self._supabase_access_token:
            if show_messages:
                QMessageBox.information(self, APP_TITLE, "Sign in to your Story Forge account first.")
            return
        if self.current_project_id is None:
            if show_messages:
                QMessageBox.information(self, APP_TITLE, "Create or select a project before syncing.")
            return
        if self._cloud_sync_busy:
            return
        self._cloud_sync_busy = True
        try:
            project = self.db.get_project(self.current_project_id)
            data = self.db.export_project(self.current_project_id)
            # Store the complete project snapshot in the existing per-user RLS table.
            params = urllib.parse.urlencode({
                "select": "id",
                "user_id": "eq." + self._supabase_user_id,
                "name": "eq." + project["name"],
            })
            existing = self._supabase_request(
                "/rest/v1/user_projects?" + params, token=self._supabase_access_token
            )
            payload = {
                "user_id": self._supabase_user_id,
                "name": project["name"],
                "project_data": data,
                "updated_at": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
            }
            if existing:
                row_id = existing[0]["id"]
                self._supabase_request(
                    "/rest/v1/user_projects?id=eq." + urllib.parse.quote(row_id, safe=""),
                    method="PATCH", payload=payload, token=self._supabase_access_token,
                    prefer="return=minimal",
                )
            else:
                self._supabase_request(
                    "/rest/v1/user_projects", method="POST", payload=payload,
                    token=self._supabase_access_token, prefer="return=minimal",
                )
            self._cloud_last_payload = data
            self.statusBar().showMessage(
                f"Cloud snapshot synced: {project['name']}", 6000
            )
        except Exception as exc:
            self.statusBar().showMessage("Cloud sync failed; local data is safe. " + str(exc)[:180], 10000)
            if show_messages:
                QMessageBox.warning(
                    self, APP_TITLE,
                    "Cloud sync failed. Your local project has not been changed.\\n\\n" + str(exc)
                )
        finally:
            self._cloud_sync_busy = False

    def _export_workspace(self):
        if not self._require_project():
            return
        project = self.db.get_project(self.current_project_id)
        target_dir = QFileDialog.getExistingDirectory(
            self, "Choose export destination folder"
        )
        if not target_dir:
            return

        slug = safe_slug(project["name"])
        bundle_dir = os.path.join(target_dir, f"{slug}_export")
        os.makedirs(bundle_dir, exist_ok=True)

        try:
            data = self.db.export_project(self.current_project_id)
            json_path = os.path.join(bundle_dir, f"{slug}_data.json")
            with open(json_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)

            font_note = "No generated font on record for this project."
            font_path = project.get("font_path", "")
            if font_path and os.path.isfile(font_path):
                shutil.copy2(font_path, bundle_dir)
                font_note = f"Included font asset: {os.path.basename(font_path)}"

            archive_path = shutil.make_archive(bundle_dir, "zip", bundle_dir)
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Export failed:\n{exc}")
            return

        QMessageBox.information(
            self,
            "Export Complete",
            "Workspace exported successfully.\n\n"
            f"Bundle folder: {bundle_dir}\n"
            f"Standalone archive: {archive_path}\n"
            f"{font_note}",
        )
        self.statusBar().showMessage(f"Exported workspace to {archive_path}")

    def _export_sections_docx(self):
        if not self._require_project():
            return
        project = self.db.get_project(self.current_project_id)

        default_name = f"{safe_slug(project['name'])}_sections.zip"
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Sections as DOCX (zip)", default_name, "Zip Archive (*.zip)"
        )
        if not dest:
            return
        if not dest.lower().endswith(".zip"):
            dest += ".zip"

        try:
            from docx_export import export_sections_to_zip
        except ImportError:
            QMessageBox.critical(
                self, APP_TITLE,
                "This export needs the 'python-docx' package.\n\n"
                "Install it with:\n    pip install python-docx",
            )
            return

        try:
            written = export_sections_to_zip(
                self.db, self.current_project_id, project["name"], dest
            )
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"DOCX export failed:\n{exc}")
            return

        QMessageBox.information(
            self, "Export Complete",
            "Created one .docx per section:\n\n" + "\n".join(written) +
            f"\n\nSaved to:\n{dest}",
        )
        self.statusBar().showMessage(f"Exported {len(written)} section documents to {dest}")

    # ------------------------------------------------------------------
    # Project plumbing
    # ------------------------------------------------------------------
    def _require_project(self):
        if self.current_project_id is None:
            QMessageBox.information(
                self, APP_TITLE, "Create or select a project first."
            )
            return False
        return True

    def _create_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if not ok or not name.strip():
            return
        try:
            project_id = self.db.create_project(name)
        except Exception:
            QMessageBox.warning(
                self, APP_TITLE, "A project with that name already exists."
            )
            return
        self._reload_projects(select_id=project_id)
        self.statusBar().showMessage(f"Project '{name.strip()}' created")

    def _delete_project(self):
        if not self._require_project():
            return
        project = self.db.get_project(self.current_project_id)
        confirm = QMessageBox.question(
            self,
            "Delete Project",
            f"Delete '{project['name']}' and ALL of its characters, "
            "languages and lexicon entries? This cannot be undone.",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_project(self.current_project_id)
            self.current_project_id = None
            self._reload_projects()

    def _reload_projects(self, select_id=None):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        projects = self.db.list_projects()
        for project in projects:
            self.project_combo.addItem(project["name"], project["id"])
        self.project_combo.blockSignals(False)

        if not projects:
            self.current_project_id = None
            self._refresh_all_modules()
            return

        if select_id is not None:
            index = self.project_combo.findData(select_id)
            self.project_combo.setCurrentIndex(max(index, 0))
        self._on_project_changed(self.project_combo.currentIndex())

    def _on_project_changed(self, index):
        if index < 0:
            self.current_project_id = None
        else:
            self.current_project_id = self.project_combo.itemData(index)
        self._refresh_all_modules()

    def _refresh_all_modules(self):
        self.current_character_id = None
        self.current_language_id = None
        self.current_location_id = None
        self.current_event_id = None
        self.current_creature_id = None
        self.current_magic_id = None
        self.current_religion_id = None
        self.current_era_id = None
        self.current_manuscript_id = None
        self.current_chapter_id = None
        self._clear_character_form()
        self._clear_language_form()
        self._clear_location_form()
        self._clear_event_form()
        self._clear_creature_form()
        self._clear_magic_form()
        self._clear_religion_form()
        self._clear_era_form()
        self._reload_characters()
        self._reload_languages()
        self._reload_locations()
        self._reload_events()
        self._reload_creatures()
        self._reload_magic_systems()
        self._reload_religions()
        self._reload_eras()
        self._reload_manuscripts()
        if self.current_project_id is not None:
            project = self.db.get_project(self.current_project_id)
            self.statusBar().showMessage(f"Active project: {project['name']}")
        else:
            self.statusBar().showMessage("No project selected.")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    db = Database()
    window = MainWindow(db)
    window.show()
    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
