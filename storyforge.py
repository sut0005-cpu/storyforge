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

import collections
import difflib
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QLineF, QByteArray
from PyQt6.QtGui import (
    QFont, QFontDatabase, QSyntaxHighlighter, QTextCharFormat, QColor,
    QTextCursor, QPainter, QPen, QBrush, QPixmap, QImage,
)
from PyQt6.QtWidgets import (
    QApplication,
    QAction,
    QComboBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QGraphicsWidget,
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
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

import threading
import urllib.request
import urllib.error
import urllib.parse
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
/* ── Base ───────────────────────────────────────────────────────────── */
QWidget {
    background-color: #1e1f24;
    color: #e8e6e3;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background-color: #17181c; }

/* ── Tabs (inner content tabs like character profile/voice) ─────────── */
QTabWidget::pane {
    border: 1px solid #2e3038;
    border-radius: 0 6px 6px 6px;
    background-color: #1e1f24;
    top: -1px;
}
QTabBar::tab {
    background: #26272e; color: #9e9b96;
    padding: 6px 14px; margin-right: 1px;
    border: 1px solid #2e3038;
    border-bottom: none;
    border-top-left-radius: 5px; border-top-right-radius: 5px;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: #1e1f24; color: #ffb454;
    border-color: #2e3038;
}
QTabBar::tab:hover:!selected { background: #2a2b31; color: #e8e6e3; }

/* ── Buttons ────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #2e3038;
    border: 1px solid #3a3d4a;
    border-radius: 5px;
    padding: 5px 12px;
    min-height: 26px;
    color: #d8d6d3;
    font-size: 12px;
}
QPushButton:hover { background-color: #3a3d4a; color: #ffffff; }
QPushButton:pressed { background-color: #252730; }
QPushButton:disabled { color: #4a4d58; background-color: #22232a; border-color: #2a2b31; }
QPushButton#accent {
    background-color: #b3541e;
    border-color: #c76030;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#accent:hover { background-color: #c96020; }
QPushButton#accent:pressed { background-color: #9a4418; }
QPushButton#accent:disabled { background-color: #5a2a0f; border-color: #6a3215; color: #888; }

/* ── Toolbar pill groups ────────────────────────────────────────────── */
QFrame#toolGroup {
    background-color: #26272e;
    border: 1px solid #34363e;
    border-radius: 6px;
}
QFrame#toolGroup QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px 10px;
    min-height: 22px;
    font-size: 12px;
    color: #c8c6c3;
}
QFrame#toolGroup QPushButton:hover { background-color: #34363e; color: #ffffff; }
QFrame#toolGroup QPushButton:pressed { background-color: #202228; }
QFrame#toolGroup QPushButton#accent {
    background-color: #b3541e; color: #ffffff; font-weight: 600;
    border-radius: 4px;
}
QFrame#toolGroup QPushButton#accent:hover { background-color: #c96020; }

/* ── Sidebar navigation ─────────────────────────────────────────────── */
QListWidget#navList {
    background-color: #17181c;
    border: none;
    border-radius: 0;
    outline: none;
    padding: 6px 0;
    font-size: 13px;
}
QListWidget#navList::item {
    padding: 7px 12px 7px 16px;
    color: #9e9b96;
    border-left: 3px solid transparent;
    border-radius: 0;
    min-height: 18px;
}
QListWidget#navList::item:hover:!selected {
    background-color: #21222a;
    color: #d8d6d3;
}
QListWidget#navList::item:selected {
    background-color: #232530;
    color: #ffb454;
    border-left: 3px solid #ffb454;
}

/* ── Inputs ─────────────────────────────────────────────────────────── */
QLineEdit, QPlainTextEdit {
    background-color: #232429;
    border: 1px solid #3a3d4a;
    border-radius: 5px;
    padding: 5px 8px;
    color: #e8e6e3;
    selection-background-color: #b3541e;
    selection-color: #ffffff;
}
QLineEdit:focus, QPlainTextEdit:focus { border-color: #ffb454; }
QLineEdit:disabled, QPlainTextEdit:disabled { color: #555860; background-color: #1e1f24; }

QTextEdit {
    background-color: #232429;
    border: 1px solid #3a3d4a;
    border-radius: 5px;
    padding: 6px 8px;
    color: #e8e6e3;
    selection-background-color: #b3541e;
    selection-color: #ffffff;
    line-height: 1.4;
}
QTextEdit:focus { border-color: #ffb454; }

QComboBox {
    background-color: #232429;
    border: 1px solid #3a3d4a;
    border-radius: 5px;
    padding: 4px 8px;
    color: #e8e6e3;
    min-height: 26px;
    font-size: 12px;
}
QComboBox:focus { border-color: #ffb454; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background-color: #232429;
    border: 1px solid #3a3d4a;
    selection-background-color: #b3541e;
    selection-color: #ffffff;
    color: #e8e6e3;
    outline: none;
    padding: 2px;
}

QSpinBox {
    background-color: #232429;
    border: 1px solid #3a3d4a;
    border-radius: 5px;
    padding: 4px 6px;
    color: #e8e6e3;
    min-height: 26px;
}
QSpinBox:focus { border-color: #ffb454; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #2e3038; border: none; width: 18px; border-radius: 3px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #3a3d4a; }

/* ── Lists & tables ─────────────────────────────────────────────────── */
QListWidget {
    background-color: #1e1f24;
    border: 1px solid #2e3038;
    border-radius: 6px;
    alternate-background-color: #21222a;
    color: #e8e6e3;
    outline: none;
    padding: 2px;
}
QListWidget::item {
    padding: 6px 10px;
    border-radius: 4px;
    min-height: 18px;
}
QListWidget::item:hover { background: #2a2b31; }
QListWidget::item:selected { background: #3a2010; color: #ffb454; }

QTableWidget {
    background-color: #1e1f24;
    border: 1px solid #2e3038;
    border-radius: 6px;
    gridline-color: #2a2b31;
    color: #e8e6e3;
    outline: none;
}
QTableWidget::item { padding: 5px 8px; }
QTableWidget::item:selected { background: #3a2010; color: #ffb454; }
QTableWidget::item:hover { background: #2a2b31; }

QHeaderView::section {
    background-color: #232429;
    color: #9e9b96;
    padding: 6px 10px;
    border: none;
    border-right: 1px solid #2e3038;
    border-bottom: 1px solid #2e3038;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QHeaderView::section:last { border-right: none; }
QHeaderView { background-color: #232429; }

/* ── Splitter ───────────────────────────────────────────────────────── */
QSplitter::handle { background-color: #2e3038; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

/* ── GroupBox ───────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #2e3038;
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px 8px 8px 8px;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    color: #9e9b96;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── CheckBox ───────────────────────────────────────────────────────── */
QCheckBox { color: #d8d6d3; spacing: 7px; font-size: 12px; }
QCheckBox::indicator {
    width: 15px; height: 15px;
    border: 1px solid #3a3d4a;
    border-radius: 3px;
    background: #232429;
}
QCheckBox::indicator:hover { border-color: #ffb454; }
QCheckBox::indicator:checked {
    background-color: #b3541e;
    border-color: #c76030;
    image: none;
}

/* ── Slider ─────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px; background: #2e3038; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #ffb454; border: none;
    width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #b3541e; border-radius: 2px; }

/* ── Progress bar ───────────────────────────────────────────────────── */
QProgressBar {
    border: 1px solid #2e3038;
    border-radius: 4px;
    background-color: #232429;
    color: #9e9b96;
    text-align: center;
    font-size: 11px;
    min-height: 16px;
}
QProgressBar::chunk { background-color: #b3541e; border-radius: 3px; margin: 1px; }

/* ── Scrollbars ─────────────────────────────────────────────────────── */
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical {
    background: #3a3d4a; border-radius: 4px; min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #555870; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 0; }
QScrollBar::handle:horizontal {
    background: #3a3d4a; border-radius: 4px; min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #555870; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Labels ─────────────────────────────────────────────────────────── */
QLabel#sectionTitle { font-size: 15px; font-weight: 700; color: #ffb454; }
QLabel#statusHint { color: #6d6a65; font-size: 11px; font-style: italic; }

/* ── Dialogs ────────────────────────────────────────────────────────── */
QMessageBox { background-color: #232429; }
QToolTip {
    background-color: #2e3038;
    color: #e8e6e3;
    border: 1px solid #3a3d4a;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}

/* ── Status bar ─────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #111214;
    color: #6d6a65;
    font-size: 11px;
    border-top: 1px solid #2e3038;
}

/* ── Menu ───────────────────────────────────────────────────────────── */
QMenuBar { background-color: #17181c; color: #c8c6c3; font-size: 12px; }
QMenuBar::item { padding: 4px 10px; }
QMenuBar::item:selected { background: #26272e; color: #ffffff; }
QMenu {
    background-color: #232429;
    border: 1px solid #3a3d4a;
    color: #e8e6e3;
    padding: 4px 0;
}
QMenu::item { padding: 6px 24px 6px 12px; font-size: 12px; }
QMenu::item:selected { background: #b3541e; color: #ffffff; }
QMenu::separator { height: 1px; background: #2e3038; margin: 4px 8px; }
"""


def safe_slug(text):
    cleaned = re.sub(r"[^A-Za-z0-9_\-]+", "_", text.strip())
    return cleaned.strip("_") or "project"


# ---------------------------------------------------------------------------
# Spell-check support
# ---------------------------------------------------------------------------

# Map friendly display names to pyspellchecker language codes.
SPELL_LANGUAGES = {
    "English":    "en",
    "Spanish":    "es",
    "French":     "fr",
    "German":     "de",
    "Italian":    "it",
    "Portuguese": "pt",
    "Russian":    "ru",
    "Arabic":     "ar",
    "Dutch":      "nl",
    "Latvian":    "lv",
    "Basque":     "eu",
    "Persian":    "fa",
}


def _build_lexicon_only_checker(words):
    """Return a SpellChecker that ONLY knows the supplied words.

    Words not in this list are flagged as misspelled.
    Returns None if pyspellchecker is unavailable.
    """
    try:
        from spellchecker import SpellChecker  # type: ignore
    except ImportError:
        return None
    checker = SpellChecker(language=None, case_sensitive=False)
    if words:
        checker.word_frequency.load_words(words)
    return checker


def _build_spell_checker(lang_code: str, extra_words=None):
    """Return a SpellChecker for *lang_code*, with *extra_words* added.

    Returns None if pyspellchecker is not installed.
    """
    try:
        from spellchecker import SpellChecker  # type: ignore
    except ImportError:
        return None
    checker = SpellChecker(language=lang_code, case_sensitive=False)
    if extra_words:
        checker.word_frequency.load_words(extra_words)
    return checker


class SpellCheckHighlighter(QSyntaxHighlighter):
    """Underlines misspelled words in red.

    Re-uses a SpellChecker instance supplied at construction time.
    Pass ``spell=None`` to disable highlighting silently.
    """

    _WORD_RE = re.compile(r"\b[A-Za-z']+\b")

    def __init__(self, document, spell=None):
        super().__init__(document)
        self._spell = spell
        self._fmt = QTextCharFormat()
        self._fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        self._fmt.setUnderlineColor(QColor("#e05050"))

    def set_spell(self, spell):
        """Swap in a new SpellChecker and rehighlight."""
        self._spell = spell
        self.rehighlight()

    def highlightBlock(self, text: str):
        if self._spell is None:
            return
        for match in self._WORD_RE.finditer(text):
            word = match.group()
            # skip short tokens, contractions, all-caps abbreviations
            if len(word) <= 1 or word.isupper():
                continue
            if self._spell.unknown([word]):
                self.setFormat(match.start(), len(word), self._fmt)


class SpellCheckTextEdit(QTextEdit):
    """QTextEdit with right-click context menu offering spelling suggestions."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._highlighter: SpellCheckHighlighter | None = None
        self._spell = None

    def attach_highlighter(self, spell):
        self._spell = spell
        self._highlighter = SpellCheckHighlighter(self.document(), spell)

    def set_spell(self, spell):
        self._spell = spell
        if self._highlighter:
            self._highlighter.set_spell(spell)
        else:
            self._highlighter = SpellCheckHighlighter(self.document(), spell)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText()

        if word and self._spell and self._spell.unknown([word]):
            suggestions = self._spell.candidates(word) or []
            if suggestions:
                menu.addSeparator()
                spell_menu = menu.addMenu(f"Spelling: “{word}”")
                for suggestion in list(suggestions)[:8]:
                    action = spell_menu.addAction(suggestion)
                    # capture variables for lambda
                    action.triggered.connect(
                        lambda _, c=cursor, s=suggestion: self._replace_word(c, s)
                    )
            else:
                menu.addSeparator()
                menu.addAction("(No suggestions)").setEnabled(False)

        menu.exec(event.globalPos())

    def _replace_word(self, cursor, replacement):
        cursor.insertText(replacement)




# ===========================================================================
# Theme support
# ===========================================================================

LIGHT_STYLESHEET = """
QWidget {
    background-color: #f5f5f0;
    color: #2a2a2a;
    font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}
QMainWindow { background-color: #eceae5; }

QTabWidget::pane { border: 1px solid #c0bfbb; border-radius: 6px; background-color: #f5f5f0; }
QTabBar::tab {
    background: #dcdcd7; color: #555555; padding: 8px 16px;
    border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px;
}
QTabBar::tab:selected { background: #ffffff; color: #b3541e; }
QTabBar::tab:hover:!selected { background: #cececa; color: #2a2a2a; }

QPushButton {
    background-color: #dcdcd7; border: 1px solid #aaaaaa;
    border-radius: 5px; padding: 5px 10px; min-height: 28px; color: #2a2a2a;
}
QPushButton:hover { background-color: #c8c8c3; }
QPushButton:pressed { background-color: #b8b8b3; }
QPushButton:disabled { color: #aaaaaa; background-color: #e8e8e3; border-color: #cccccc; }
QPushButton#accent {
    background-color: #b3541e; border-color: #d97734;
    color: #ffffff; font-weight: bold;
}
QPushButton#accent:hover { background-color: #d2691e; }

QLineEdit, QPlainTextEdit {
    background-color: #ffffff; border: 1px solid #aaaaaa;
    border-radius: 5px; padding: 5px; color: #2a2a2a;
    selection-background-color: #b3541e; selection-color: #ffffff;
}
QLineEdit:focus, QPlainTextEdit:focus { border-color: #b3541e; }

QTextEdit {
    background-color: #ffffff; border: 1px solid #aaaaaa;
    border-radius: 5px; padding: 5px; color: #2a2a2a;
    selection-background-color: #b3541e; selection-color: #ffffff;
}
QTextEdit:focus { border-color: #b3541e; }

QComboBox {
    background-color: #ffffff; border: 1px solid #aaaaaa;
    border-radius: 5px; padding: 4px 8px; color: #2a2a2a; min-height: 26px;
}
QComboBox:focus { border-color: #b3541e; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #ffffff; border: 1px solid #aaaaaa;
    selection-background-color: #b3541e; selection-color: #ffffff;
    color: #2a2a2a; outline: none;
}

QListWidget, QTableWidget {
    background-color: #fafaf5; border: 1px solid #aaaaaa;
    border-radius: 5px; alternate-background-color: #f0f0eb; color: #2a2a2a;
    outline: none;
}
QListWidget::item { padding: 6px; border-radius: 3px; }
QListWidget::item:hover { background: #ebe9e4; }
QListWidget::item:selected { background: #b3541e; color: #ffffff; }
QTableWidget::item { padding: 4px; color: #2a2a2a; }
QTableWidget::item:selected { background: #b3541e; color: #ffffff; }
QTableWidget::item:hover { background: #ebe9e4; }

QHeaderView::section {
    background-color: #dcdcd7; color: #b3541e;
    padding: 6px 8px; border: none; border-right: 1px solid #aaaaaa;
    border-bottom: 1px solid #aaaaaa; font-weight: 500;
}
QHeaderView::section:horizontal:last { border-right: none; }

QSplitter::handle { background-color: #c0bfbb; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

QGroupBox {
    border: 1px solid #c0bfbb; border-radius: 6px;
    margin-top: 10px; padding-top: 8px; color: #2a2a2a; font-weight: 500;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 10px; padding: 0 4px; color: #b3541e;
}

QCheckBox { color: #2a2a2a; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px; border: 1px solid #aaaaaa;
    border-radius: 3px; background: #ffffff;
}
QCheckBox::indicator:checked { background: #b3541e; border-color: #d97734; }
QCheckBox::indicator:hover { border-color: #b3541e; }

QSpinBox {
    background-color: #ffffff; border: 1px solid #aaaaaa;
    border-radius: 5px; padding: 4px 6px; color: #2a2a2a; min-height: 26px;
}
QSpinBox:focus { border-color: #b3541e; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #dcdcd7; border: none; width: 16px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #c8c8c3; }

QSlider::groove:horizontal {
    height: 4px; background: #c0bfbb; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #b3541e; border: none;
    width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #d97734; border-radius: 2px; }

QProgressBar {
    border: 1px solid #aaaaaa; border-radius: 4px;
    background-color: #f0f0eb; color: #2a2a2a;
    text-align: center; font-size: 11px; min-height: 18px;
}
QProgressBar::chunk { background-color: #b3541e; border-radius: 3px; }

QScrollBar:vertical {
    background: #f0f0eb; width: 10px; margin: 0; border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #aaaaaa; border-radius: 5px; min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #888888; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #f0f0eb; height: 10px; margin: 0; border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #aaaaaa; border-radius: 5px; min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background: #888888; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QLabel#sectionTitle { font-size: 17px; font-weight: bold; color: #b3541e; }
QLabel#statusHint { color: #777770; font-style: italic; }

QDialog { background-color: #f5f5f0; }
QMessageBox { background-color: #ffffff; }
QToolTip {
    background-color: #ffffff; color: #2a2a2a;
    border: 1px solid #aaaaaa; border-radius: 4px; padding: 4px 6px;
}
QStatusBar { background-color: #eceae5; color: #777770; }
QMenuBar { background-color: #f5f5f0; color: #2a2a2a; }
QMenuBar::item:selected { background: #dcdcd7; }
QMenu { background-color: #ffffff; border: 1px solid #aaaaaa; color: #2a2a2a; }
QMenu::item:selected { background: #b3541e; color: #ffffff; }
QMenu::separator { height: 1px; background: #c0bfbb; margin: 3px 0; }
"""

# ===========================================================================
# Find & Replace Dialog
# ===========================================================================

class FindReplaceDialog(QDialog):
    def __init__(self, text_edit: QTextEdit, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find & Replace")
        self.setMinimumWidth(400)
        self._edit = text_edit
        layout = QVBoxLayout(self)

        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("Find:"))
        self.find_edit = QLineEdit()
        find_row.addWidget(self.find_edit)
        layout.addLayout(find_row)

        rep_row = QHBoxLayout()
        rep_row.addWidget(QLabel("Replace:"))
        self.replace_edit = QLineEdit()
        rep_row.addWidget(self.replace_edit)
        layout.addLayout(rep_row)

        opts_row = QHBoxLayout()
        self.case_check = QCheckBox("Case sensitive")
        self.whole_check = QCheckBox("Whole word")
        opts_row.addWidget(self.case_check)
        opts_row.addWidget(self.whole_check)
        opts_row.addStretch(1)
        layout.addLayout(opts_row)

        btn_row = QHBoxLayout()
        find_btn = QPushButton("Find Next")
        find_btn.clicked.connect(self._find_next)
        rep_btn = QPushButton("Replace")
        rep_btn.clicked.connect(self._replace_one)
        rep_all_btn = QPushButton("Replace All")
        rep_all_btn.clicked.connect(self._replace_all)
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusHint")
        btn_row.addWidget(find_btn)
        btn_row.addWidget(rep_btn)
        btn_row.addWidget(rep_all_btn)
        btn_row.addWidget(self.status_label)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

    def _flags(self):
        return Qt.FindFlag(0) | (Qt.FindFlag.FindCaseSensitively if self.case_check.isChecked() else Qt.FindFlag(0)) | (Qt.FindFlag.FindWholeWords if self.whole_check.isChecked() else Qt.FindFlag(0))

    def _find_next(self):
        term = self.find_edit.text()
        if not term:
            return False
        found = self._edit.find(term, self._flags())
        if not found:
            # wrap around
            cur = self._edit.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Start)
            self._edit.setTextCursor(cur)
            found = self._edit.find(term, self._flags())
        self.status_label.setText("" if found else "Not found")
        return found

    def _replace_one(self):
        cur = self._edit.textCursor()
        if cur.hasSelection():
            cur.insertText(self.replace_edit.text())
        self._find_next()

    def _replace_all(self):
        term = self.find_edit.text()
        repl = self.replace_edit.text()
        if not term:
            return
        doc = self._edit.document()
        content = doc.toPlainText()
        flags = re.IGNORECASE if not self.case_check.isChecked() else 0
        pattern = r'\b' + re.escape(term) + r'\b' if self.whole_check.isChecked() else re.escape(term)
        new_content, count = re.subn(pattern, repl, content, flags=flags)
        if count:
            self._edit.setPlainText(new_content)
        self.status_label.setText(f"{count} replaced" if count else "Not found")


# ===========================================================================
# Word Statistics Dialog
# ===========================================================================

class WordStatsDialog(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Word Statistics")
        self.setMinimumSize(420, 480)
        layout = QVBoxLayout(self)

        words = re.findall(r"\b[a-zA-Z']+\b", text)
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # Counts
        counts_group = QGroupBox("Counts")
        cg = QFormLayout(counts_group)
        cg.addRow("Words:", QLabel(f"{len(words):,}"))
        cg.addRow("Characters:", QLabel(f"{len(text):,}"))
        cg.addRow("Sentences:", QLabel(f"{len(sentences):,}"))
        cg.addRow("Paragraphs:", QLabel(f"{len(paragraphs):,}"))
        avg_sent = round(len(words) / max(len(sentences), 1), 1)
        cg.addRow("Avg words/sentence:", QLabel(str(avg_sent)))
        # Flesch reading ease (approximate)
        syllables = sum(max(1, len(re.findall(r"[aeiouAEIOU]+", w))) for w in words)
        if words and sentences:
            flesch = 206.835 - 1.015*(len(words)/len(sentences)) - 84.6*(syllables/max(len(words),1))
            flesch = max(0, min(100, round(flesch, 1)))
        else:
            flesch = 0
        cg.addRow("Readability (Flesch):", QLabel(f"{flesch}/100"))
        layout.addWidget(counts_group)

        # Top words
        freq_group = QGroupBox("Top 20 Words")
        fg = QVBoxLayout(freq_group)
        stopwords = {"the","a","an","and","or","but","in","on","at","to","for","of","with","it","is","was","are","were","be","been","i","he","she","they","we","you","that","this","had","have","has","not","from","as","by","his","her","their","our","my","me","him","us","them","its","if","up","do","did","so","no","all","what","there"}
        counter = collections.Counter(w.lower() for w in words if w.lower() not in stopwords and len(w) > 2)
        freq_table = QTableWidget(0, 2)
        freq_table.setHorizontalHeaderLabels(["Word", "Count"])
        freq_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        freq_table.setMaximumHeight(200)
        for word, count in counter.most_common(20):
            r = freq_table.rowCount()
            freq_table.insertRow(r)
            freq_table.setItem(r, 0, QTableWidgetItem(word))
            freq_table.setItem(r, 1, QTableWidgetItem(str(count)))
        fg.addWidget(freq_table)
        layout.addWidget(freq_group)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# ===========================================================================
# Revision History Dialog
# ===========================================================================

class RevisionHistoryDialog(QDialog):
    def __init__(self, db, chapter_id: int, current_body: str, parent=None):
        super().__init__(parent)
        self.db = db
        self.chapter_id = chapter_id
        self.current_body = current_body
        # Only metadata loaded here; full body fetched on demand
        self._revisions = db.list_chapter_revisions(chapter_id)
        self._loaded_bodies: dict[int, str] = {}  # rev_id -> body
        self.setWindowTitle("Revision History")
        self.setMinimumSize(960, 620)

        main = QVBoxLayout(self)
        main.setSpacing(8)

        # Header info
        info = QLabel(f"{len(self._revisions)} snapshot(s) — select one to preview the diff against the current text.")
        info.setObjectName("statusHint")
        main.addWidget(info)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: revision list
        left = QWidget()
        left.setMaximumWidth(230)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(QLabel("Snapshots (newest first)"))
        self.rev_list = QListWidget()
        self.rev_list.setAlternatingRowColors(True)
        if not self._revisions:
            self.rev_list.addItem(QListWidgetItem("No snapshots yet"))
        for rev in self._revisions:
            self.rev_list.addItem(QListWidgetItem(rev["saved_at"]))
        self.rev_list.currentRowChanged.connect(self._on_rev_selected)
        lv.addWidget(self.rev_list, 1)

        btn_row = QHBoxLayout()
        restore_btn = QPushButton("Restore This Version")
        restore_btn.setObjectName("accent")
        restore_btn.clicked.connect(self._restore)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(restore_btn)
        btn_row.addWidget(close_btn)
        lv.addLayout(btn_row)
        splitter.addWidget(left)

        # Right: tabbed view — diff and snapshot text
        right_tabs = QTabWidget()

        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setFont(QFont("Consolas", 10))
        self.diff_view.setPlaceholderText("Select a snapshot on the left to see the diff.")
        right_tabs.addTab(self.diff_view, "Diff (snapshot → current)")

        self.snapshot_view = QTextEdit()
        self.snapshot_view.setReadOnly(True)
        self.snapshot_view.setFont(QFont("Georgia", 11))
        self.snapshot_view.setPlaceholderText("Select a snapshot to read its full text.")
        right_tabs.addTab(self.snapshot_view, "Snapshot text")

        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 740])
        main.addWidget(splitter, 1)

        # Auto-select first item
        if self._revisions:
            self.rev_list.setCurrentRow(0)

    def _get_body(self, row: int) -> str:
        """Fetch body for the given row, caching to avoid repeated DB hits."""
        rev = self._revisions[row]
        rev_id = rev["id"]
        if rev_id not in self._loaded_bodies:
            full = self.db.get_chapter_revision(rev_id)
            self._loaded_bodies[rev_id] = full["body"] if full else ""
        return self._loaded_bodies[rev_id]

    def _on_rev_selected(self, row):
        if row < 0 or row >= len(self._revisions):
            self.diff_view.clear()
            self.snapshot_view.clear()
            return

        old_body = self._get_body(row)
        self.snapshot_view.setPlainText(old_body)

        diff = difflib.unified_diff(
            old_body.splitlines(keepends=True),
            self.current_body.splitlines(keepends=True),
            fromfile=f"snapshot ({self._revisions[row]['saved_at']})",
            tofile="current",
            lineterm="",
        )

        html_lines = []
        for line in diff:
            esc = _html_esc(line)
            if line.startswith("+") and not line.startswith("+++"):
                html_lines.append(f'<span style="background:#1a3a1a;color:#6dcc6d;">{esc}</span>')
            elif line.startswith("-") and not line.startswith("---"):
                html_lines.append(f'<span style="background:#3a1a1a;color:#e07070;">{esc}</span>')
            elif line.startswith("@@"):
                html_lines.append(f'<span style="color:#88aacc;font-style:italic;">{esc}</span>')
            elif line.startswith("+++") or line.startswith("---"):
                html_lines.append(f'<span style="color:#aaaaaa;">{esc}</span>')
            else:
                html_lines.append(f'<span style="color:#c8c6c3;">{esc}</span>')

        if html_lines:
            self.diff_view.setHtml(
                "<pre style='font-family:Consolas,monospace;font-size:11px;"
                "line-height:1.4;padding:8px;'>"
                + "".join(f"{ln}<br>" for ln in html_lines)
                + "</pre>"
            )
        else:
            self.diff_view.setHtml(
                "<p style='color:#888;padding:12px;'>No differences — this snapshot is identical to the current text.</p>"
            )

    def _restore(self):
        row = self.rev_list.currentRow()
        if row < 0 or not self._revisions:
            QMessageBox.information(self, "Restore", "Select a snapshot first.")
            return
        saved_at = self._revisions[row]["saved_at"]
        reply = QMessageBox.question(
            self, "Restore Version",
            f"Replace the current chapter text with the snapshot from {saved_at}?\n\nThis cannot be undone (though the current version will itself be saved as a new snapshot first).",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.restored_body = self._get_body(row)
            self.accept()

def _html_esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")


# ===========================================================================
# Relationship Web (QGraphicsScene-based)
# ===========================================================================

RELATIONSHIP_TYPES = ["ally", "enemy", "family", "romantic", "rival", "mentor", "other"]
REL_COLORS = {
    "ally":     "#5fad56",
    "enemy":    "#e05050",
    "family":   "#ffb454",
    "romantic": "#e878a0",
    "rival":    "#7788dd",
    "mentor":   "#77ccaa",
    "other":    "#888888",
}


class RelationshipWebWidget(QWidget):
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self._node_positions: dict[int, tuple] = {}  # char_id -> (x, y)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        add_rel_btn = QPushButton("Add Relationship")
        add_rel_btn.clicked.connect(self._add_relationship)
        del_rel_btn = QPushButton("Remove Selected")
        del_rel_btn.clicked.connect(self._remove_relationship)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(add_rel_btn)
        toolbar.addWidget(del_rel_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        layout.addWidget(self.view, 1)

        # Legend
        legend_row = QHBoxLayout()
        for rel_type, color in REL_COLORS.items():
            dot = QLabel(f"● {rel_type}")
            dot.setStyleSheet(f"color:{color}; font-size:11px;")
            legend_row.addWidget(dot)
        legend_row.addStretch(1)
        layout.addLayout(legend_row)

        self.refresh()

    def refresh(self):
        self.scene.clear()
        self._node_positions.clear()
        if not self.project_id:
            return
        chars = self.db.list_characters(self.project_id)
        rels  = self.db.list_relationships(self.project_id)
        if not chars:
            return

        # Arrange nodes in a circle
        cx, cy, radius = 400, 300, 220
        n = len(chars)
        char_items = {}
        for i, char in enumerate(chars):
            angle = 2 * math.pi * i / max(n, 1)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            self._node_positions[char["id"]] = (x, y)

            # Draw ellipse node
            ellipse = self.scene.addEllipse(x-40, y-18, 80, 36,
                QPen(QColor("#ffb454"), 2), QBrush(QColor("#2a2b31")))
            ellipse.setZValue(2)
            text = self.scene.addText(char["name"][:14], QFont("Segoe UI", 9))
            text.setDefaultTextColor(QColor("#e8e6e3"))
            text.setPos(x - text.boundingRect().width()/2, y - 9)
            text.setZValue(3)
            char_items[char["id"]] = ellipse

        # Draw relationship lines
        for rel in rels:
            cid_a, cid_b = rel["char_a_id"], rel["char_b_id"]
            if cid_a not in self._node_positions or cid_b not in self._node_positions:
                continue
            ax, ay = self._node_positions[cid_a]
            bx, by = self._node_positions[cid_b]
            color = REL_COLORS.get(rel["relationship"].lower(), "#888888")
            line = self.scene.addLine(ax, ay, bx, by, QPen(QColor(color), 2))
            line.setZValue(1)
            # midpoint label
            mx, my = (ax+bx)/2, (ay+by)/2
            lbl = self.scene.addText(rel["relationship"], QFont("Segoe UI", 8))
            lbl.setDefaultTextColor(QColor(color))
            lbl.setPos(mx, my)
            lbl.setZValue(4)

    def _add_relationship(self):
        chars = self.db.list_characters(self.project_id)
        if len(chars) < 2:
            QMessageBox.information(self.parent(), "Relationship Web", "Need at least 2 characters.")
            return
        char_names = [c["name"] for c in chars]
        char_ids   = [c["id"]   for c in chars]

        dlg = QDialog(self)
        dlg.setWindowTitle("Add Relationship")
        form = QFormLayout(dlg)
        combo_a = QComboBox(); combo_a.addItems(char_names)
        combo_b = QComboBox(); combo_b.addItems(char_names)
        combo_b.setCurrentIndex(1)
        combo_rel = QComboBox(); combo_rel.addItems(RELATIONSHIP_TYPES)
        notes_edit = QLineEdit()
        form.addRow("Character A:", combo_a)
        form.addRow("Character B:", combo_b)
        form.addRow("Relationship:", combo_rel)
        form.addRow("Notes:", notes_edit)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        a_idx = combo_a.currentIndex()
        b_idx = combo_b.currentIndex()
        if a_idx == b_idx:
            QMessageBox.warning(self, "Relationship Web", "Choose two different characters.")
            return
        self.db.upsert_relationship(
            self.project_id, char_ids[a_idx], char_ids[b_idx],
            combo_rel.currentText(), notes_edit.text()
        )
        self.refresh()

    def _remove_relationship(self):
        rels = self.db.list_relationships(self.project_id)
        if not rels:
            return
        items = [f"{r['char_a_name']} ↔ {r['char_b_name']} ({r['relationship']})" for r in rels]
        name, ok = QInputDialog.getItem(self, "Remove Relationship", "Select:", items, editable=False)
        if not ok:
            return
        idx = items.index(name)
        r = rels[idx]
        self.db.delete_relationship(self.project_id, r["char_a_id"], r["char_b_id"])
        self.refresh()


# ===========================================================================
# World Map Canvas
# ===========================================================================

class WorldMapWidget(QWidget):
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self._pixmap = QPixmap(1200, 700)
        self._pixmap.fill(QColor("#1a3a2a"))
        self._pins: list[dict] = []
        self._draw_color = QColor("#ffffff")
        self._brush_size = 8
        self._last_pos = None
        self._tool = "draw"  # draw | erase | pin
        self._pending_pin_color = "#ffb454"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        tb = QHBoxLayout()
        draw_btn  = QPushButton("✏ Draw")
        draw_btn.clicked.connect(lambda: self._set_tool("draw"))
        erase_btn = QPushButton("⬜ Erase")
        erase_btn.clicked.connect(lambda: self._set_tool("erase"))
        pin_btn   = QPushButton("📍 Add Pin")
        pin_btn.clicked.connect(lambda: self._set_tool("pin"))
        clear_btn = QPushButton("Clear Canvas")
        clear_btn.clicked.connect(self._clear_canvas)
        save_btn  = QPushButton("Save Map")
        save_btn.setObjectName("accent")
        save_btn.clicked.connect(self._save_map)
        load_btn  = QPushButton("Load Map Image")
        load_btn.clicked.connect(self._load_map_image)
        export_btn = QPushButton("Export PNG")
        export_btn.clicked.connect(self._export_png)

        self.color_label = QLabel("  Color  ")
        self.color_label.setStyleSheet("background:#ffffff; border:1px solid #666; min-width:40px;")
        self.color_label.mousePressEvent = self._pick_color

        self.brush_spin = QSpinBox()
        self.brush_spin.setRange(1, 60)
        self.brush_spin.setValue(8)
        self.brush_spin.valueChanged.connect(lambda v: setattr(self, "_brush_size", v))

        for w in [draw_btn, erase_btn, pin_btn, QLabel("Color:"), self.color_label,
                  QLabel("Size:"), self.brush_spin, clear_btn, save_btn, load_btn, export_btn]:
            tb.addWidget(w)
        tb.addStretch(1)
        layout.addLayout(tb)

        self.canvas = _MapCanvas(self)
        layout.addWidget(self.canvas, 1)

        self._load_from_db()

    def _set_tool(self, tool):
        self._tool = tool
        if tool == "draw":
            self.canvas.setCursor(Qt.CursorShape.CrossCursor)
        elif tool == "erase":
            self.canvas.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.canvas.setCursor(Qt.CursorShape.PointingHandCursor)

    def _pick_color(self, _event=None):
        from PyQt6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(self._draw_color, self)
        if c.isValid():
            self._draw_color = c
            self.color_label.setStyleSheet(f"background:{c.name()}; border:1px solid #666; min-width:40px;")

    def _clear_canvas(self):
        self._pixmap.fill(QColor("#1a3a2a"))
        self.canvas.update()

    def _load_map_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load background image", "", "Images (*.png *.jpg *.bmp)")
        if path:
            loaded = QPixmap(path)
            if not loaded.isNull():
                self._pixmap = loaded.scaled(1200, 700, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
                self.canvas.update()

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export map as PNG", "world_map.png", "PNG (*.png)")
        if path:
            # Render pins onto the exported image
            export_px = QPixmap(self._pixmap)
            painter = QPainter(export_px)
            self._draw_pins_on(painter)
            painter.end()
            export_px.save(path, "PNG")

    def _save_map(self):
        if not self.project_id:
            return
        ba = QByteArray()
        from PyQt6.QtCore import QBuffer
        buf = QBuffer(ba)
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        self._pixmap.save(buf, "PNG")
        self.db.save_map_image(self.project_id, bytes(ba))

    def _load_from_db(self):
        if not self.project_id:
            return
        img_bytes = self.db.get_map_image(self.project_id)
        if img_bytes:
            px = QPixmap()
            px.loadFromData(img_bytes)
            if not px.isNull():
                self._pixmap = px
        self._pins = self.db.list_map_pins(self.project_id)
        self.canvas.update()

    def refresh(self):
        self._load_from_db()

    def _draw_pins_on(self, painter):
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        for pin in self._pins:
            x = int(pin["x"] * self.canvas.width())
            y = int(pin["y"] * self.canvas.height())
            painter.setPen(QPen(QColor(pin.get("color","#ffb454")), 3))
            painter.setBrush(QBrush(QColor(pin.get("color","#ffb454"))))
            painter.drawEllipse(x-7, y-7, 14, 14)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(x+10, y+5, pin.get("label",""))

    def _add_pin_at(self, x_frac, y_frac):
        locations = self.db.list_locations(self.project_id) if self.project_id else []
        loc_names = ["(none)"] + [l["name"] for l in locations]
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Map Pin")
        form = QFormLayout(dlg)
        label_edit = QLineEdit()
        loc_combo = QComboBox(); loc_combo.addItems(loc_names)
        color_combo = QComboBox(); color_combo.addItems(["#ffb454","#e05050","#5fad56","#77aaff","#ff88cc","#ffffff"])
        form.addRow("Label:", label_edit)
        form.addRow("Link location:", loc_combo)
        form.addRow("Color:", color_combo)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        label = label_edit.text().strip() or "Pin"
        loc_idx = loc_combo.currentIndex() - 1
        loc_id = locations[loc_idx]["id"] if loc_idx >= 0 else None
        color = color_combo.currentText()
        self.db.upsert_map_pin(self.project_id, label, x_frac, y_frac, color, loc_id)
        self._pins = self.db.list_map_pins(self.project_id)
        self.canvas.update()


class _MapCanvas(QWidget):
    def __init__(self, map_widget: "WorldMapWidget"):
        super().__init__(map_widget)
        self._mw = map_widget
        self.setMinimumHeight(500)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, _e):
        painter = QPainter(self)
        # Scale pixmap to widget size
        painter.drawPixmap(self.rect(), self._mw._pixmap)
        self._mw._draw_pins_on(painter)
        painter.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._mw._last_pos = e.position()
            if self._mw._tool == "pin":
                xf = e.position().x() / self.width()
                yf = e.position().y() / self.height()
                self._mw._add_pin_at(xf, yf)
                return
            self._paint_at(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._mw._tool in ("draw","erase"):
            self._paint_at(e.position())

    def mouseReleaseEvent(self, _e):
        self._mw._last_pos = None

    def _paint_at(self, pos):
        # Map widget coords to pixmap coords
        px = self._mw._pixmap
        sx = px.width()  / self.width()
        sy = px.height() / self.height()
        painter = QPainter(self._mw._pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        size = self._mw._brush_size
        if self._mw._tool == "erase":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#1a3a2a")))
            painter.drawEllipse(QPointF(pos.x()*sx, pos.y()*sy), size, size)
        else:
            painter.setPen(QPen(self._mw._draw_color, size*2, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            if self._mw._last_pos:
                lp = self._mw._last_pos
                painter.drawLine(QPointF(lp.x()*sx, lp.y()*sy), QPointF(pos.x()*sx, pos.y()*sy))
            else:
                painter.drawPoint(QPointF(pos.x()*sx, pos.y()*sy))
        painter.end()
        self._mw._last_pos = pos
        self.update()


# ===========================================================================
# Name Generator
# ===========================================================================

class NameGeneratorWidget(QWidget):
    # Built-in phonology presets
    PRESETS = {
        "Fantasy (soft)":  dict(onset=["s","l","r","m","n","th","al","el","ae"],
                                 vowel=["a","e","i","o","ae","ai","ie","ea"],
                                 coda=["n","r","l","s","th","nd","r","l",""],
                                 min_syl=2, max_syl=4),
        "Fantasy (harsh)": dict(onset=["kr","dr","gr","str","vr","gh","kh","th","z"],
                                 vowel=["a","u","o","ar","ur"],
                                 coda=["k","g","r","n","st","xt",""],
                                 min_syl=1, max_syl=3),
        "Nordic":          dict(onset=["b","d","f","g","h","j","k","l","m","n","r","s","t","v"],
                                 vowel=["a","e","i","o","u","ø","æ","å","ei","ou"],
                                 coda=["r","n","k","g","m","nd","ng",""],
                                 min_syl=1, max_syl=3),
        "Asian-inspired":  dict(onset=["sh","zh","ch","x","m","n","l","t","k","h","w","y"],
                                 vowel=["a","e","i","o","u","ai","ao","ei","ie","uo"],
                                 coda=["n","ng",""],
                                 min_syl=1, max_syl=3),
    }

    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header = QLabel("Name Generator")
        header.setObjectName("sectionTitle")
        layout.addWidget(header)

        # Settings
        settings = QHBoxLayout()
        settings.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(self.PRESETS.keys()))
        self.preset_combo.addItem("From project language")
        settings.addWidget(self.preset_combo)

        settings.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("(any)")
        settings.addWidget(self.lang_combo)

        settings.addWidget(QLabel("Count:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 50)
        self.count_spin.setValue(10)
        settings.addWidget(self.count_spin)

        gen_btn = QPushButton("Generate Names")
        gen_btn.setObjectName("accent")
        gen_btn.clicked.connect(self._generate)
        settings.addWidget(gen_btn)
        settings.addStretch(1)
        layout.addLayout(settings)

        # Custom phonology
        custom_group = QGroupBox("Custom Phonology (comma-separated lists)")
        cg = QFormLayout(custom_group)
        self.onset_edit  = QLineEdit(); self.onset_edit.setPlaceholderText("s, l, th, str, ...")
        self.vowel_edit  = QLineEdit(); self.vowel_edit.setPlaceholderText("a, e, ai, ie, ...")
        self.coda_edit   = QLineEdit(); self.coda_edit.setPlaceholderText("n, r, nd, (blank for none), ...")
        self.syl_min_spin = QSpinBox(); self.syl_min_spin.setRange(1,5); self.syl_min_spin.setValue(2)
        self.syl_max_spin = QSpinBox(); self.syl_max_spin.setRange(1,6); self.syl_max_spin.setValue(3)
        cg.addRow("Onsets:", self.onset_edit)
        cg.addRow("Vowels:", self.vowel_edit)
        cg.addRow("Codas:", self.coda_edit)
        syl_row = QHBoxLayout()
        syl_row.addWidget(QLabel("Min syllables:"))
        syl_row.addWidget(self.syl_min_spin)
        syl_row.addWidget(QLabel("Max:"))
        syl_row.addWidget(self.syl_max_spin)
        syl_row.addStretch(1)
        cg.addRow(syl_row)
        layout.addWidget(custom_group)

        # Result
        self.result_list = QListWidget()
        self.result_list.setAlternatingRowColors(True)
        layout.addWidget(self.result_list, 1)

        copy_btn = QPushButton("Copy Selected to Clipboard")
        copy_btn.clicked.connect(self._copy_selected)
        add_char_btn = QPushButton("Add as Character Name")
        add_char_btn.clicked.connect(self._add_as_character)
        btn_row = QHBoxLayout()
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(add_char_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

    def refresh(self):
        self.lang_combo.clear()
        self.lang_combo.addItem("(any)")
        if self.project_id:
            for lang in self.db.list_languages(self.project_id):
                self.lang_combo.addItem(lang["name"])

    def _get_phonology(self):
        preset_name = self.preset_combo.currentText()
        # Custom overrides preset if any field filled
        onset_text = self.onset_edit.text().strip()
        vowel_text = self.vowel_edit.text().strip()
        if onset_text and vowel_text:
            onset = [x.strip() for x in onset_text.split(",") if x.strip()]
            vowel = [x.strip() for x in vowel_text.split(",") if x.strip()]
            coda  = [x.strip() for x in self.coda_edit.text().split(",")] if self.coda_edit.text().strip() else [""]
            return dict(onset=onset, vowel=vowel, coda=coda,
                        min_syl=self.syl_min_spin.value(), max_syl=self.syl_max_spin.value())
        if preset_name == "From project language":
            # Derive phonology from selected language lexicon
            lang_name = self.lang_combo.currentText()
            if self.project_id and lang_name != "(any)":
                for lang in self.db.list_languages(self.project_id):
                    if lang["name"] == lang_name:
                        words = [e["word"] for e in self.db.list_lexicon(lang["id"])]
                        return self._derive_phonology(words)
            return self.PRESETS["Fantasy (soft)"]
        return self.PRESETS.get(preset_name, self.PRESETS["Fantasy (soft)"])

    def _derive_phonology(self, words):
        """Very rough phonology extraction from a word list."""
        import random
        onsets, vowels, codas = set(), set(), set()
        vowel_chars = set("aeiouáéíóúàèìòùäëïöü")
        for w in words:
            w = w.lower()
            # collect initial consonant clusters up to first vowel
            m = re.match(r"^([^aeiouáéíóú]*)([aeiouáéíóú]+)([^aeiouáéíóú]*)", w)
            if m:
                if m.group(1): onsets.add(m.group(1))
                if m.group(2): vowels.add(m.group(2))
                if m.group(3): codas.add(m.group(3))
        if not onsets: onsets = {"s","l","m","n","r","k"}
        if not vowels: vowels = {"a","e","i","o"}
        codas.add("")
        return dict(onset=list(onsets), vowel=list(vowels), coda=list(codas), min_syl=2, max_syl=3)

    def _make_name(self, phon):
        import random
        n_syl = random.randint(phon["min_syl"], phon["max_syl"])
        name = ""
        for i in range(n_syl):
            name += random.choice(phon["onset"])
            name += random.choice(phon["vowel"])
            if i == n_syl - 1:
                name += random.choice(phon["coda"])
        return name.capitalize()

    def _generate(self):
        import random
        phon = self._get_phonology()
        count = self.count_spin.value()
        self.result_list.clear()
        seen = set()
        attempts = 0
        while len(seen) < count and attempts < count * 20:
            name = self._make_name(phon)
            if name not in seen:
                seen.add(name)
                self.result_list.addItem(name)
            attempts += 1

    def _copy_selected(self):
        items = self.result_list.selectedItems()
        if items:
            QApplication.clipboard().setText(", ".join(i.text() for i in items))

    def _add_as_character(self):
        items = self.result_list.selectedItems()
        if not items or not self.project_id:
            return
        for item in items:
            self.db.create_character(self.project_id, item.text())
        QMessageBox.information(self.parent(), "Name Generator",
                                f"Added {len(items)} character(s) to the project.")


# ===========================================================================
# Lore Bible export (HTML)
# ===========================================================================

def export_lore_bible(db, project_id: int, output_path: str):
    data = db.export_project(project_id)
    project_name = data["project"]["name"]

    def section(title, content_html):
        return (f"<section><h2>{title}</h2>{content_html}</section>")

    def card(title, rows):
        inner = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k,v in rows)
        return f"<div class='card'><h3>{title}</h3><table>{inner}</table></div>"

    # Characters
    chars_html = ""
    for c in data.get("characters", []):
        rows = [("Role", c["role"]), ("Bio", c["bio"][:300]+"..." if len(c["bio"])>300 else c["bio"])]
        rows += list(c.get("custom_attributes",{}).items())
        chars_html += card(c["name"], rows)

    # Languages + lexicon
    langs_html = ""
    for lang in data.get("languages", []):
        lex_rows = "".join(
            f"<tr><td><b>{e['word']}</b></td><td>{e['translation']}</td><td>{e['part_of_speech']}</td><td>{e['notes']}</td></tr>"
            for e in lang.get("lexicon", [])
        )
        lex_table = f"<table class='lex'><thead><tr><th>Word</th><th>Translation</th><th>POS</th><th>Notes</th></tr></thead><tbody>{lex_rows}</tbody></table>" if lex_rows else "<p>No lexicon entries.</p>"
        langs_html += f"<div class='card'><h3>{lang['name']}</h3><p>{lang['grammar_documentation'][:500]}</p>{lex_table}</div>"

    # Locations
    locs_html = ""
    for loc in data.get("locations", []):
        rows = [("Type",loc["type"]),("Climate",loc["climate"]),("Population",loc["population"]),("Description",loc["description"][:200])]
        locs_html += card(loc["name"], rows)

    # Magic systems
    magic_html = ""
    for ms in data.get("magic_systems", []):
        rows = [("Classification",ms["classification"]),("Source",ms["source"]),("Rules",ms["rules"][:300]),("Limitations",ms["limitations"][:200]),("Cost",ms["cost"])]
        magic_html += card(ms["name"], rows)

    # Timeline
    timeline_html = "<table class='lex'><thead><tr><th>Era</th><th>Start</th><th>End</th><th>Description</th></tr></thead><tbody>"
    for era in data.get("timeline", []):
        timeline_html += f"<tr><td><b>{era['name']}</b></td><td>{era['start_label']}</td><td>{era['end_label']}</td><td>{era['description'][:200]}</td></tr>"
    timeline_html += "</tbody></table>"

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{project_name} — Lore Bible</title>
<style>
*{{box-sizing:border-box;}} body{{font-family:'Segoe UI',sans-serif;background:#1a1b21;color:#e8e6e3;margin:0;padding:24px;}}
h1{{color:#ffb454;border-bottom:2px solid #ffb454;padding-bottom:8px;}}
h2{{color:#ffb454;margin-top:32px;}} h3{{color:#d97734;}}
section{{margin-bottom:40px;}}
.card{{background:#26272e;border:1px solid #3a3c46;border-radius:8px;padding:16px;margin-bottom:16px;display:inline-block;min-width:280px;vertical-align:top;margin-right:16px;}}
table{{border-collapse:collapse;width:100%;}} th,td{{padding:6px 10px;border:1px solid #3a3c46;text-align:left;}}
th{{background:#2e3038;color:#ffb454;}} tr:nth-child(even){{background:#2a2b31;}}
table.lex th{{font-size:12px;}} a{{color:#ffb454;}}
.toc a{{display:block;margin:4px 0;}}
</style></head><body>
<h1>📖 {project_name} — Lore Bible</h1>
<p>Generated by Story Forge · {data["exported_at"]}</p>
<nav class="toc">
<h2>Contents</h2>
<a href="#characters">Characters</a><a href="#languages">Languages &amp; Lexicons</a>
<a href="#locations">Locations</a><a href="#magic">Magic Systems</a>
<a href="#timeline">Timeline</a>
</nav>
{section('<span id="characters">Characters</span>', chars_html or "<p>No characters.</p>")}
{section('<span id="languages">Languages &amp; Lexicons</span>', langs_html or "<p>No languages.</p>")}
{section('<span id="locations">Locations</span>', locs_html or "<p>No locations.</p>")}
{section('<span id="magic">Magic Systems</span>', magic_html or "<p>No magic systems.</p>")}
{section('<span id="timeline">Timeline</span>', timeline_html)}
</body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)




# ===========================================================================
# Tension curve canvas (used inside MainWindow._show_tension_curve)
# ===========================================================================

class _TensionCanvas(QWidget):
    def __init__(self, cards, parent=None):
        super().__init__(parent)
        self._cards = cards
        self.setMinimumHeight(220)

    def paintEvent(self, _e):
        if not self._cards:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad = 40
        n = len(self._cards)
        tensions = [c.get('tension', 3) for c in self._cards]
        step = (w - 2*pad) / max(n - 1, 1)

        # Grid lines
        p.setPen(QPen(QColor("#3a3c46"), 1))
        for t in range(1, 6):
            y = h - pad - (t-1) * (h-2*pad) / 4
            p.drawLine(pad, int(y), w-pad, int(y))
            p.drawText(4, int(y)+5, str(t))

        # Line
        p.setPen(QPen(QColor("#ffb454"), 2))
        points = []
        for i, t in enumerate(tensions):
            x = pad + i * step
            y = h - pad - (t-1) * (h-2*pad) / 4
            points.append((x, y))

        for i in range(len(points)-1):
            p.drawLine(int(points[i][0]), int(points[i][1]),
                       int(points[i+1][0]), int(points[i+1][1]))

        # Dots + labels
        p.setPen(QPen(QColor("#e8e6e3"), 1))
        p.setBrush(QBrush(QColor("#b3541e")))
        for i, (x, y) in enumerate(points):
            p.drawEllipse(int(x)-5, int(y)-5, 10, 10)
            lbl = self._cards[i].get('chapter_title', '')[:12]
            p.drawText(int(x)-20, h-8, lbl)
        p.end()


# ===========================================================================
# Split-screen manuscript dialog
# ===========================================================================

class _SplitScreenDialog(QDialog):
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.setWindowTitle("Split Screen — Manuscript View")
        self.setMinimumSize(1100, 600)
        layout = QHBoxLayout(self)

        # Collect all chapters
        self._chapters = []
        if project_id:
            for ms in db.list_manuscripts(project_id):
                for ch in db.list_chapters(ms['id']):
                    self._chapters.append({'ms': ms['title'], **ch})

        ch_titles = [f"{c['ms']} / {c['title']}" for c in self._chapters]

        for side in ('left', 'right'):
            panel = QWidget()
            pv = QVBoxLayout(panel)
            combo = QComboBox()
            combo.addItems(ch_titles)
            if side == 'right' and len(ch_titles) > 1:
                combo.setCurrentIndex(1)
            editor = QTextEdit()
            editor.setReadOnly(True)
            editor.setFont(QFont("Georgia", 11))
            combo.currentIndexChanged.connect(
                lambda idx, e=editor: self._load_chapter(idx, e)
            )
            self._load_chapter(combo.currentIndex(), editor)
            pv.addWidget(combo)
            pv.addWidget(editor, 1)
            layout.addWidget(panel, 1)
            if side == 'left':
                self._left_combo, self._left_editor = combo, editor
            else:
                self._right_combo, self._right_editor = combo, editor

    def _load_chapter(self, idx, editor):
        if 0 <= idx < len(self._chapters):
            editor.setPlainText(self._chapters[idx].get('body', ''))



# ===========================================================================
# Plot Thread Tracker
# ===========================================================================
THREAD_COLORS = ["#ffb454","#e05050","#5fad56","#77aaff","#e878a0","#77ccaa","#cc88ff","#ff8844"]

class PlotThreadWidget(QWidget):
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.current_manuscript_id = None
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        hdr = QLabel("Plot Thread Tracker")
        hdr.setObjectName("sectionTitle")
        layout.addWidget(hdr)

        tb = QHBoxLayout()
        add_btn = QPushButton("New Thread")
        add_btn.clicked.connect(self._add_thread)
        del_btn = QPushButton("Delete Thread")
        del_btn.clicked.connect(self._delete_thread)
        self.ms_combo = QComboBox()
        self.ms_combo.currentIndexChanged.connect(self._refresh_map)
        tb.addWidget(QLabel("Manuscript:"))
        tb.addWidget(self.ms_combo)
        tb.addSpacing(8)
        tb.addWidget(add_btn)
        tb.addWidget(del_btn)
        tb.addStretch(1)
        layout.addLayout(tb)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Thread list
        left = QWidget(); left.setMaximumWidth(200)
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0)
        lv.addWidget(QLabel("Threads"))
        self.thread_list = QListWidget()
        self.thread_list.setAlternatingRowColors(True)
        lv.addWidget(self.thread_list, 1)
        splitter.addWidget(left)

        # Map canvas
        self.map_view = QTextEdit()
        self.map_view.setReadOnly(True)
        self.map_view.setFont(QFont("Consolas", 10))
        self.map_view.setPlaceholderText("Tag chapters with plot threads to see the map here.")
        splitter.addWidget(self.map_view)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        layout.addWidget(QLabel("Tip: open a chapter in the Manuscripts tab and use Link Plot Threads to tag it.", objectName="statusHint"))

    def refresh(self, project_id=None, manuscript_id=None):
        if project_id is not None:
            self.project_id = project_id
        self.ms_combo.blockSignals(True)
        self.ms_combo.clear()
        if self.project_id:
            for ms in self.db.list_manuscripts(self.project_id):
                self.ms_combo.addItem(ms["title"], ms["id"])
        self.ms_combo.blockSignals(False)
        self._reload_threads()
        self._refresh_map()

    def _reload_threads(self):
        self.thread_list.clear()
        if not self.project_id:
            return
        for t in self.db.list_plot_threads(self.project_id):
            item = QListWidgetItem(t["name"])
            item.setForeground(QColor(t["color"]))
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.thread_list.addItem(item)

    def _refresh_map(self):
        self.map_view.clear()
        ms_id = self.ms_combo.currentData()
        if not ms_id or not self.project_id:
            return
        threads = self.db.list_plot_threads(self.project_id)
        chapters = self.db.list_chapters(ms_id)
        if not threads or not chapters:
            self.map_view.setPlainText("No threads or chapters yet.")
            return
        thread_map = self.db.get_thread_chapter_map(ms_id)
        chapter_nums = [c["chapter_number"] for c in chapters]
        max_ch = max(chapter_nums) if chapter_nums else 1

        html = "<table style='border-collapse:collapse;font-family:Consolas,monospace;font-size:11px;'>"
        html += "<tr><th style='padding:4px 8px;text-align:left;color:#ffb454;'>Thread</th>"
        for ch in chapters:
            html += f"<th style='padding:4px 4px;color:#aaaaaa;'>Ch{ch['chapter_number']}</th>"
        html += "</tr>"
        for t in threads:
            active_chs = set(thread_map.get(t["id"], []))
            html += f"<tr><td style='padding:4px 8px;color:{t['color']};white-space:nowrap;'>{t['name']}</td>"
            for ch in chapters:
                if ch["chapter_number"] in active_chs:
                    html += f"<td style='text-align:center;background:{t['color']}33;color:{t['color']};'>●</td>"
                else:
                    html += "<td style='text-align:center;color:#333;'>·</td>"
            html += "</tr>"
        html += "</table>"
        self.map_view.setHtml(html)

    def _add_thread(self):
        if not self.project_id:
            return
        name, ok = QInputDialog.getText(self, "New Plot Thread", "Thread name:")
        if not ok or not name.strip():
            return
        existing = self.db.list_plot_threads(self.project_id)
        color = THREAD_COLORS[len(existing) % len(THREAD_COLORS)]
        self.db.create_plot_thread(self.project_id, name.strip(), color)
        self._reload_threads()
        self._refresh_map()

    def _delete_thread(self):
        item = self.thread_list.currentItem()
        if not item:
            return
        tid = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Delete Thread", f"Delete thread '{item.text()}'?")
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_plot_thread(tid)
            self._reload_threads()
            self._refresh_map()


# ===========================================================================
# Research Board
# ===========================================================================

class ResearchBoardWidget(QWidget):
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.current_item_id = None
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: list + tag filter
        left = QWidget(); left.setMaximumWidth(260)
        lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0)
        hdr = QLabel("Research Board"); hdr.setObjectName("sectionTitle")
        lv.addWidget(hdr)
        filter_row = QHBoxLayout()
        self.tag_filter = QLineEdit()
        self.tag_filter.setPlaceholderText("Filter by tag...")
        self.tag_filter.textChanged.connect(self._reload_list)
        filter_row.addWidget(self.tag_filter)
        lv.addLayout(filter_row)
        self.item_list = QListWidget()
        self.item_list.setAlternatingRowColors(True)
        self.item_list.currentRowChanged.connect(self._on_item_selected)
        lv.addWidget(self.item_list, 1)
        btn_row = QHBoxLayout()
        add_btn = QPushButton("New"); add_btn.clicked.connect(self._new_item)
        del_btn = QPushButton("Delete"); del_btn.clicked.connect(self._delete_item)
        btn_row.addWidget(add_btn); btn_row.addWidget(del_btn)
        lv.addLayout(btn_row)
        splitter.addWidget(left)

        # Right: editor
        right = QWidget()
        rv = QVBoxLayout(right)
        form = QFormLayout()
        self.title_edit = QLineEdit(); self.title_edit.setPlaceholderText("Title")
        self.url_edit = QLineEdit(); self.url_edit.setPlaceholderText("https://...")
        self.tags_edit = QLineEdit(); self.tags_edit.setPlaceholderText("comma, separated, tags")
        form.addRow("Title:", self.title_edit)
        form.addRow("URL:", self.url_edit)
        form.addRow("Tags:", self.tags_edit)
        rv.addLayout(form)
        rv.addWidget(QLabel("Notes:"))
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Paste reference text, quotes, notes...")
        rv.addWidget(self.content_edit, 1)
        save_btn = QPushButton("Save"); save_btn.setObjectName("accent")
        save_btn.clicked.connect(self._save_item)
        rv.addWidget(save_btn)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def refresh(self, project_id=None):
        if project_id is not None:
            self.project_id = project_id
        self._reload_list()

    def _reload_list(self):
        self.item_list.clear()
        if not self.project_id:
            return
        tag = self.tag_filter.text().strip().lower()
        for item in self.db.list_research_items(self.project_id):
            if tag and tag not in item.get("tags","").lower():
                continue
            li = QListWidgetItem(item["title"] or "(untitled)")
            li.setData(Qt.ItemDataRole.UserRole, item["id"])
            if item.get("tags"):
                li.setToolTip(item["tags"])
            self.item_list.addItem(li)

    def _on_item_selected(self, row):
        li = self.item_list.item(row)
        if not li:
            return
        item_id = li.data(Qt.ItemDataRole.UserRole)
        for item in self.db.list_research_items(self.project_id):
            if item["id"] == item_id:
                self.current_item_id = item_id
                self.title_edit.setText(item["title"])
                self.url_edit.setText(item["url"])
                self.tags_edit.setText(item["tags"])
                self.content_edit.setPlainText(item["content"])
                break

    def _new_item(self):
        if not self.project_id:
            return
        iid = self.db.create_research_item(self.project_id, "New item")
        self.current_item_id = iid
        self._reload_list()
        self.title_edit.setText("New item")
        self.url_edit.clear(); self.tags_edit.clear(); self.content_edit.clear()

    def _save_item(self):
        if not self.current_item_id:
            return
        self.db.update_research_item(
            self.current_item_id,
            self.title_edit.text(), self.content_edit.toPlainText(),
            self.url_edit.text(), self.tags_edit.text())
        self._reload_list()

    def _delete_item(self):
        li = self.item_list.currentItem()
        if not li:
            return
        reply = QMessageBox.question(self, "Delete", f"Delete '{li.text()}'?")
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_research_item(li.data(Qt.ItemDataRole.UserRole))
            self.current_item_id = None
            self._reload_list()
            self.title_edit.clear(); self.url_edit.clear()
            self.tags_edit.clear(); self.content_edit.clear()


# ===========================================================================
# Session Timer
# ===========================================================================

class SessionTimerWidget(QWidget):
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self._running = False
        self._elapsed = 0
        self._start_words = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hdr = QLabel("Writing Session Timer"); hdr.setObjectName("sectionTitle")
        layout.addWidget(hdr)

        # Clock display
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("font-size:48px;font-weight:bold;color:#ffb454;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        # WPM
        self.wpm_label = QLabel("")
        self.wpm_label.setObjectName("statusHint")
        self.wpm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.wpm_label)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Session")
        self.start_btn.setObjectName("accent")
        self.start_btn.clicked.connect(self._toggle)
        self.stop_btn = QPushButton("Stop & Save")
        self.stop_btn.clicked.connect(self._stop_save)
        self.stop_btn.setEnabled(False)
        btn_row.addStretch(1)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # Heatmap / log
        layout.addWidget(QLabel("Session Log (most recent first)"))
        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(["Date", "Duration", "Words", "WPM"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.log_table.setAlternatingRowColors(True)
        layout.addWidget(self.log_table, 1)
        layout.addStretch()

    def set_word_count_fn(self, fn):
        self._word_count_fn = fn

    def refresh(self, project_id=None):
        if project_id is not None:
            self.project_id = project_id
        self._reload_log()

    def _reload_log(self):
        self.log_table.setRowCount(0)
        if not self.project_id:
            return
        for sess in self.db.list_sessions(self.project_id):
            r = self.log_table.rowCount()
            self.log_table.insertRow(r)
            dur = sess["duration_s"]
            dur_str = f"{dur//3600:02d}:{(dur%3600)//60:02d}:{dur%60:02d}"
            wpm = round(sess["words_written"] / max(dur/60, 1), 1) if dur else 0
            self.log_table.setItem(r, 0, QTableWidgetItem(sess["date"]))
            self.log_table.setItem(r, 1, QTableWidgetItem(dur_str))
            self.log_table.setItem(r, 2, QTableWidgetItem(str(sess["words_written"])))
            self.log_table.setItem(r, 3, QTableWidgetItem(str(wpm)))

    def _toggle(self):
        if not self._running:
            self._running = True
            self._elapsed = 0
            self._start_words = self._get_words()
            self._timer.start(1000)
            self.start_btn.setText("Pause")
            self.stop_btn.setEnabled(True)
        else:
            self._running = False
            self._timer.stop()
            self.start_btn.setText("Resume")

    def _tick(self):
        self._elapsed += 1
        h, rem = divmod(self._elapsed, 3600)
        m, s = divmod(rem, 60)
        self.time_label.setText(f"{h:02d}:{m:02d}:{s:02d}")
        if self._elapsed % 10 == 0 and self._elapsed > 0:
            words_now = self._get_words()
            delta = max(0, words_now - self._start_words)
            wpm = round(delta / max(self._elapsed/60, 1), 1)
            self.wpm_label.setText(f"{delta} words this session · {wpm} wpm")

    def _stop_save(self):
        self._timer.stop()
        self._running = False
        self.start_btn.setText("Start Session")
        self.stop_btn.setEnabled(False)
        words_written = max(0, self._get_words() - self._start_words)
        if self.project_id and self._elapsed > 0:
            import datetime
            self.db.log_session(
                self.project_id,
                datetime.date.today().isoformat(),
                self._elapsed,
                words_written,
            )
        self._elapsed = 0
        self.time_label.setText("00:00:00")
        self.wpm_label.setText("")
        self._reload_log()

    def _get_words(self):
        if hasattr(self, "_word_count_fn"):
            try:
                return self._word_count_fn()
            except Exception:
                pass
        return 0


# ===========================================================================
# World Calendar
# ===========================================================================

class WorldCalendarWidget(QWidget):
    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        hdr = QLabel("In-World Calendar"); hdr.setObjectName("sectionTitle")
        layout.addWidget(hdr)

        form = QFormLayout()
        self.cal_name_edit = QLineEdit()
        self.cal_name_edit.setPlaceholderText("e.g. The Reckoning Calendar")
        self.days_spin = QSpinBox(); self.days_spin.setRange(1, 20); self.days_spin.setValue(7)
        self.week_days_edit = QLineEdit()
        self.week_days_edit.setPlaceholderText("Comma-separated day names, e.g. Moonday, Fireday, ...")
        form.addRow("Calendar name:", self.cal_name_edit)
        form.addRow("Days per week:", self.days_spin)
        form.addRow("Day names:", self.week_days_edit)
        layout.addLayout(form)

        layout.addWidget(QLabel("Months (one per line: Name, Days — e.g. Frostmere, 32)"))
        self.months_edit = QPlainTextEdit()
        self.months_edit.setPlaceholderText("Frostmere, 32\nBloomtide, 28\nScorchmonth, 30\n...")
        self.months_edit.setMaximumHeight(160)
        layout.addWidget(self.months_edit)

        layout.addWidget(QLabel("Notes / special rules:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        layout.addWidget(self.notes_edit)

        save_btn = QPushButton("Save Calendar"); save_btn.setObjectName("accent")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

        # Preview
        layout.addWidget(QLabel("Calendar summary:"))
        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        self.preview_label.setObjectName("statusHint")
        layout.addWidget(self.preview_label)
        layout.addStretch(1)

    def refresh(self, project_id=None):
        if project_id is not None:
            self.project_id = project_id
        if not self.project_id:
            return
        cal = self.db.get_calendar(self.project_id)
        if cal:
            self.cal_name_edit.setText(cal.get("calendar_name",""))
            self.days_spin.setValue(cal.get("days_per_week",7))
            self.week_days_edit.setText(
                ", ".join(json.loads(cal.get("week_day_names","[]"))))
            months = json.loads(cal.get("months_json","[]"))
            self.months_edit.setPlainText(
                "\n".join(f"{m['name']}, {m['days']}" for m in months))
            self.notes_edit.setPlainText(cal.get("notes",""))
            self._update_preview(months, cal.get("days_per_week",7))

    def _save(self):
        if not self.project_id:
            return
        months = []
        for line in self.months_edit.toPlainText().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                try:
                    months.append({"name": parts[0], "days": int(parts[1])})
                except ValueError:
                    pass
        day_names = [d.strip() for d in self.week_days_edit.text().split(",") if d.strip()]
        self.db.upsert_calendar(
            self.project_id,
            self.cal_name_edit.text() or "The Calendar",
            json.dumps(months),
            self.days_spin.value(),
            json.dumps(day_names),
            self.notes_edit.toPlainText(),
        )
        self._update_preview(months, self.days_spin.value())
        QMessageBox.information(self.parent() or self, "Calendar", "Calendar saved.")

    def _update_preview(self, months, days_per_week):
        if not months:
            self.preview_label.setText("No months defined yet.")
            return
        total_days = sum(m["days"] for m in months)
        total_weeks = round(total_days / max(days_per_week, 1), 1)
        summary = (f"{len(months)} months · {total_days} days per year · "
                   f"{total_weeks} weeks of {days_per_week} days each\n")
        summary += " · ".join(f"{m['name']} ({m['days']}d)" for m in months)
        self.preview_label.setText(summary)

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
        # Spell check state
        self._spell_lang_code: str = "en"
        self._spell_extra_words: list[str] = []
        # Registered custom fonts: family_name -> ttf_path
        self._registered_fonts: dict[str, str] = {}
        # Split screen dialog ref
        self._split_dialog = None
        self._ch_completer = None

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
        # ── Menu bar ────────────────────────────────────────────────────────
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Project",    self._create_project)
        file_menu.addAction("Delete Project", self._delete_project)
        file_menu.addSeparator()
        file_menu.addAction("Export Workspace",  self._export_workspace)
        file_menu.addAction("Export EPUB",        self._export_epub)
        file_menu.addAction("Export DOCX",        self._export_sections_docx)
        file_menu.addAction("Export Lore Bible",  self._export_lore_bible)

        cloud_menu = menubar.addMenu("Cloud")
        cloud_menu.addAction("Sign In / Account", self._cloud_account_dialog)
        cloud_menu.addAction("Sync Now",           self._cloud_sync_now)
        cloud_menu.addSeparator()
        cloud_menu.addAction("Upload File",        self._cloud_upload_file)
        cloud_menu.addAction("Browse Cloud Files", self._cloud_download_file)

        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Contradiction Detector", self._run_contradiction_detector)
        tools_menu.addAction("Toggle Light / Dark",    self._toggle_theme)

        # ── Central layout ──────────────────────────────────────────────────
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Compact toolbar ─────────────────────────────────────────────────
        toolbar_widget = QWidget()
        toolbar_widget.setFixedHeight(46)
        toolbar_widget.setStyleSheet(
            "background:#17181c; border-bottom:1px solid #2e3038;"
        )
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(10, 6, 10, 6)
        toolbar_layout.setSpacing(8)

        # Brand
        brand = QLabel("Story Forge")
        brand.setObjectName("sectionTitle")
        brand.setStyleSheet("font-size:15px;font-weight:bold;color:#ffb454;margin-right:4px;")
        toolbar_layout.addWidget(brand)

        # Separator helper
        def vline():
            f = QFrame()
            f.setFrameShape(QFrame.Shape.VLine)
            f.setStyleSheet("color:#34363e; max-width:1px;")
            return f

        # Group helper
        def btn_group(*buttons):
            frame = QFrame()
            frame.setObjectName("toolGroup")
            fl = QHBoxLayout(frame)
            fl.setContentsMargins(3, 2, 3, 2)
            fl.setSpacing(1)
            for b in buttons:
                fl.addWidget(b)
            return frame

        # Project group
        toolbar_layout.addWidget(QLabel("Project:", styleSheet="color:#8d8a85;font-size:12px;"))
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(150)
        self.project_combo.setMaximumWidth(220)
        self.project_combo.setStyleSheet("font-size:12px;min-height:24px;")
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        toolbar_layout.addWidget(self.project_combo)

        new_p = QPushButton("New"); new_p.clicked.connect(self._create_project)
        del_p = QPushButton("Delete"); del_p.clicked.connect(self._delete_project)
        toolbar_layout.addWidget(btn_group(new_p, del_p))
        toolbar_layout.addWidget(vline())

        # Export group
        exp_ws  = QPushButton("Export"); exp_ws.setObjectName("accent")
        exp_ws.clicked.connect(self._export_workspace)
        exp_ws.setToolTip("Export Workspace (JSON + zip)")
        toolbar_layout.addWidget(btn_group(exp_ws))
        toolbar_layout.addWidget(vline())

        # Cloud group
        self.account_btn = QPushButton("Sign In")
        self.account_btn.clicked.connect(self._cloud_account_dialog)
        self.account_btn.setToolTip("Story Forge Account")
        self.sync_btn = QPushButton("Sync")
        self.sync_btn.clicked.connect(self._cloud_sync_now)
        self.sync_btn.setToolTip("Sync Cloud Now")
        toolbar_layout.addWidget(btn_group(self.account_btn, self.sync_btn))
        toolbar_layout.addWidget(vline())

        # Word goal
        toolbar_layout.addWidget(QLabel("Goal:", styleSheet="color:#8d8a85;font-size:12px;"))
        self.word_goal_bar = QProgressBar()
        self.word_goal_bar.setMinimumWidth(140)
        self.word_goal_bar.setMaximumWidth(220)
        self.word_goal_bar.setMaximumHeight(18)
        self.word_goal_bar.setFormat("%v / %m (%p%)")
        self.word_goal_bar.setValue(0)
        self.word_goal_bar.setMaximum(80000)
        self.word_goal_bar.setStyleSheet("font-size:11px;")
        toolbar_layout.addWidget(self.word_goal_bar)
        set_goal_btn = QPushButton("Set")
        set_goal_btn.clicked.connect(self._set_word_goal)
        set_goal_btn.setToolTip("Set word goal")
        toolbar_layout.addWidget(btn_group(set_goal_btn))

        toolbar_layout.addStretch(1)
        root.addWidget(toolbar_widget)

        # ── Body: sidebar nav + stacked content ─────────────────────────────
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar navigation list
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setFixedWidth(158)
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

        # Nav items with group headers
        def nav_header(text):
            item = QListWidgetItem(text)
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # not selectable
            item.setForeground(QColor("#555860"))
            font = QFont()
            font.setPointSize(9)
            font.setWeight(QFont.Weight.Bold)
            item.setFont(font)
            return item

        def nav_item(text, indent=True):
            item = QListWidgetItem(("  " if indent else "") + text)
            return item

        self.nav_list.addItem(nav_header("WORLD"))
        self.nav_list.addItem(nav_item("Timeline"))
        self.nav_list.addItem(nav_item("Characters"))
        self.nav_list.addItem(nav_item("Locations"))
        self.nav_list.addItem(nav_item("Events"))
        self.nav_list.addItem(nav_item("Creatures"))
        self.nav_list.addItem(nav_item("Magic Systems"))
        self.nav_list.addItem(nav_item("Religions"))
        self.nav_list.addItem(nav_header("LANGUAGE"))
        self.nav_list.addItem(nav_item("Languages"))
        self.nav_list.addItem(nav_header("WRITING"))
        self.nav_list.addItem(nav_item("Manuscripts"))
        self.nav_list.addItem(nav_item("Plot Threads"))
        self.nav_list.addItem(nav_item("Research"))
        self.nav_list.addItem(nav_item("Session"))
        self.nav_list.addItem(nav_header("TOOLS"))
        self.nav_list.addItem(nav_item("Font Studio"))
        self.nav_list.addItem(nav_item("Rel. Web"))
        self.nav_list.addItem(nav_item("World Map"))
        self.nav_list.addItem(nav_item("Names"))
        self.nav_list.addItem(nav_item("Calendar"))
        body_layout.addWidget(self.nav_list)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#2e3038; max-width:1px;")
        body_layout.addWidget(sep)

        # Stacked tab widget (tabs hidden — nav list drives it)
        self.tabs = QTabWidget()
        self.tabs.tabBar().setVisible(False)
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border:none; border-radius:0; background:#1e1f24; }"
            "QTabWidget > QWidget { margin:0; padding:0; }"
        )

        def _padded(widget, h=14, v=12):
            """Wrap a tab content widget with consistent padding."""
            w = QWidget()
            lyt = QVBoxLayout(w)
            lyt.setContentsMargins(h, v, h, v)
            lyt.setSpacing(0)
            lyt.addWidget(widget)
            return w

        # Build pages in the same order as nav items (skipping headers)
        self.tabs.addTab(_padded(self._build_timeline_tab()),        "Timeline")
        self.tabs.addTab(_padded(self._build_characters_tab()),      "Characters")
        self.tabs.addTab(_padded(self._build_locations_tab()),       "Locations")
        self.tabs.addTab(_padded(self._build_events_tab()),          "Events")
        self.tabs.addTab(_padded(self._build_creatures_tab()),       "Creatures")
        self.tabs.addTab(_padded(self._build_magic_tab()),           "Magic Systems")
        self.tabs.addTab(_padded(self._build_religions_tab()),       "Religions")
        self.tabs.addTab(_padded(self._build_languages_tab()),       "Languages")
        self.tabs.addTab(_padded(self._build_manuscripts_tab()),     "Manuscripts")
        self.tabs.addTab(_padded(self._build_plot_threads_tab()),    "Plot Threads")
        self.tabs.addTab(_padded(self._build_research_board_tab()), "Research")
        self.tabs.addTab(_padded(self._build_session_timer_tab()),   "Session")
        self.tabs.addTab(_padded(self._build_font_studio_tab()),     "Font Studio")
        self.tabs.addTab(_padded(self._build_relationship_web_tab()),"Rel. Web")
        self.tabs.addTab(_padded(self._build_world_map_tab(), h=0, v=0), "World Map")
        self.tabs.addTab(_padded(self._build_name_generator_tab()),  "Names")
        self.tabs.addTab(_padded(self._build_world_calendar_tab()),  "Calendar")

        body_layout.addWidget(self.tabs, 1)
        root.addWidget(body, 1)

        # Map selectable nav rows to tab indices
        # Nav row -> tab index (-1 = header, skip)
        self._nav_row_to_tab = {
            1: 0,   # Timeline
            2: 1,   # Characters
            3: 2,   # Locations
            4: 3,   # Events
            5: 4,   # Creatures
            6: 5,   # Magic Systems
            7: 6,   # Religions
            9: 7,   # Languages
            11: 8,  # Manuscripts
            12: 9,  # Plot Threads
            13: 10, # Research
            14: 11, # Session
            16: 12, # Font Studio
            17: 13, # Rel. Web
            18: 14, # World Map
            19: 15, # Names
            20: 16, # Calendar
        }

        self.setCentralWidget(central)
        # Select Manuscripts by default
        self.nav_list.setCurrentRow(11)
        self.statusBar().showMessage("Ready")

    def _on_nav_changed(self, row):
        tab_idx = self._nav_row_to_tab.get(row, -1)
        if tab_idx >= 0:
            self.tabs.setCurrentIndex(tab_idx)

    def _switch_to_tab(self, name: str):
        """Switch nav to a tab by name string — used by feature buttons."""
        for row, idx in self._nav_row_to_tab.items():
            if self.tabs.tabText(idx) == name:
                self.nav_list.setCurrentRow(row)
                break

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

        # Voice Profile tab
        voice_tab = QWidget()
        vt_layout = QVBoxLayout(voice_tab)
        vt_layout.setSpacing(6)
        vt_form = QFormLayout()
        self.voice_vocab_edit   = QLineEdit(); self.voice_vocab_edit.setPlaceholderText("Formal, archaic, slang-heavy, terse...")
        self.voice_quirks_edit  = QLineEdit(); self.voice_quirks_edit.setPlaceholderText("Never finishes sentences, over-explains...")
        self.voice_never_edit   = QLineEdit(); self.voice_never_edit.setPlaceholderText("Words this character would never use")
        self.voice_accent_edit  = QLineEdit(); self.voice_accent_edit.setPlaceholderText("Regional dialect, dropped letters...")
        self.voice_example_edit = QTextEdit(); self.voice_example_edit.setMaximumHeight(100)
        self.voice_example_edit.setPlaceholderText("Example lines in their voice...")
        vt_form.addRow("Vocabulary style:", self.voice_vocab_edit)
        vt_form.addRow("Speech quirks:",    self.voice_quirks_edit)
        vt_form.addRow("Never says:",       self.voice_never_edit)
        vt_form.addRow("Accent / dialect:", self.voice_accent_edit)
        vt_form.addRow("Example lines:",    self.voice_example_edit)
        vt_layout.addLayout(vt_form)
        save_voice_btn = QPushButton("Save Voice Profile")
        save_voice_btn.setObjectName("accent")
        save_voice_btn.clicked.connect(self._save_voice_profile)
        vt_layout.addWidget(save_voice_btn)
        vt_layout.addStretch(1)

        # Wrap profile + voice in tabs
        char_right_tabs = QTabWidget()
        char_right_tabs.addTab(right, "Profile")
        char_right_tabs.addTab(voice_tab, "Voice Profile")

        splitter.addWidget(left)
        splitter.addWidget(char_right_tabs)
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
        self._load_voice_profile(char_id)

    def _save_voice_profile(self):
        if self.current_character_id is None:
            return
        self.db.upsert_voice_profile(
            self.current_character_id,
            self.voice_vocab_edit.text(),
            self.voice_quirks_edit.text(),
            self.voice_never_edit.text(),
            self.voice_accent_edit.text(),
            self.voice_example_edit.toPlainText(),
        )
        self.statusBar().showMessage("Voice profile saved.")

    def _load_voice_profile(self, char_id):
        if not hasattr(self, "voice_vocab_edit"):
            return
        p = self.db.get_voice_profile(char_id)
        self.voice_vocab_edit.setText(p.get("vocabulary", ""))
        self.voice_quirks_edit.setText(p.get("speech_quirks", ""))
        self.voice_never_edit.setText(p.get("never_says", ""))
        self.voice_accent_edit.setText(p.get("accent_notes", ""))
        self.voice_example_edit.setPlainText(p.get("example_lines", ""))

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
        if hasattr(self, "voice_vocab_edit"):
            self.voice_vocab_edit.clear()
            self.voice_quirks_edit.clear()
            self.voice_never_edit.clear()
            self.voice_accent_edit.clear()
            self.voice_example_edit.clear()

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
        # Refresh spell checker so new lexicon words are recognised
        self._refresh_spell_checker()

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
        self.crt_notes_edit.setPlaceholderText("DM/Author notes, variants…")
        nl.addWidget(self.crt_notes_edit)
        tabs_inner.addTab(notes_w, "Notes")

        # Stat block tab
        stat_w = QWidget()
        stat_layout = QFormLayout(stat_w)
        self.crt_threat_combo = QComboBox()
        self.crt_threat_combo.addItems(["Trivial","Low","Medium","High","Deadly","Legendary"])
        self.crt_speed_edit   = QLineEdit(); self.crt_speed_edit.setPlaceholderText("30ft walking, 60ft flying...")
        self.crt_senses_edit  = QLineEdit(); self.crt_senses_edit.setPlaceholderText("Darkvision 120ft, tremorsense...")
        self.crt_lang_edit    = QLineEdit(); self.crt_lang_edit.setPlaceholderText("Common, Draconic, telepathy...")
        self.crt_drops_edit   = QLineEdit(); self.crt_drops_edit.setPlaceholderText("Scales, venom sac, heart core...")
        self.crt_encounter_edit = QTextEdit(); self.crt_encounter_edit.setMaximumHeight(70)
        self.crt_encounter_edit.setPlaceholderText("Typical encounter scenario or tactics...")
        stat_layout.addRow("Threat level:", self.crt_threat_combo)
        stat_layout.addRow("Speed:",        self.crt_speed_edit)
        stat_layout.addRow("Senses:",       self.crt_senses_edit)
        stat_layout.addRow("Languages:",    self.crt_lang_edit)
        stat_layout.addRow("Drops / loot:", self.crt_drops_edit)
        stat_layout.addRow("Encounter:",    self.crt_encounter_edit)
        tabs_inner.addTab(stat_w, "Stat Block")

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
        template_btn = QPushButton("From Template")
        template_btn.clicked.connect(self._new_chapter_from_template)
        ch_header_row.addStretch(1)
        ch_header_row.addWidget(new_ch_btn)
        ch_header_row.addWidget(template_btn)
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

        # ── Spell-check + font toolbar ─────────────────────────────────────
        spell_bar = QHBoxLayout()
        spell_bar.setSpacing(8)
        spell_bar.setContentsMargins(0, 4, 0, 4)

        spell_lbl = QLabel("Spell")
        spell_lbl.setStyleSheet("color:#6d6a65;font-size:11px;")
        spell_bar.addWidget(spell_lbl)

        self.spell_lang_combo = QComboBox()
        self.spell_lang_combo.setMaximumWidth(118)
        self.spell_lang_combo.addItem("Off")
        for _sln in SPELL_LANGUAGES:
            self.spell_lang_combo.addItem(_sln)
        self.spell_lang_combo.setCurrentText("English")
        self.spell_lang_combo.currentTextChanged.connect(self._on_spell_lang_changed)
        spell_bar.addWidget(self.spell_lang_combo)

        self.spell_lexicon_check = QCheckBox("Lexicon")
        self.spell_lexicon_check.setChecked(True)
        self.spell_lexicon_check.stateChanged.connect(self._on_spell_lang_changed)
        spell_bar.addWidget(self.spell_lexicon_check)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color:#2e3038;max-width:1px;")
        spell_bar.addWidget(sep1)

        font_lbl = QLabel("Font")
        font_lbl.setStyleSheet("color:#6d6a65;font-size:11px;")
        spell_bar.addWidget(font_lbl)

        self.ch_font_combo = QComboBox()
        self.ch_font_combo.addItem("Default")
        self.ch_font_combo.setMinimumWidth(120)
        self.ch_font_combo.setMaximumWidth(190)
        self.ch_font_combo.currentTextChanged.connect(self._on_chapter_font_changed)
        spell_bar.addWidget(self.ch_font_combo)

        self.ch_font_size_spin = QComboBox()
        self.ch_font_size_spin.setMaximumWidth(58)
        for _fsz in ["10","11","12","13","14","16","18","20","24"]:
            self.ch_font_size_spin.addItem(_fsz)
        self.ch_font_size_spin.setCurrentText("12")
        self.ch_font_size_spin.currentTextChanged.connect(self._on_chapter_font_changed)
        spell_bar.addWidget(self.ch_font_size_spin)

        spell_bar.addStretch(1)
        chv.addLayout(spell_bar)

        body_lbl = QLabel("Body")
        body_lbl.setStyleSheet("color:#6d6a65;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-top:2px;")
        chv.addWidget(body_lbl)
        self.ch_body_edit = SpellCheckTextEdit()
        chv.addWidget(self.ch_body_edit, 1)

        chv.addWidget(QLabel("Notes:"))
        self.ch_notes_edit = QTextEdit()
        self.ch_notes_edit.setMaximumHeight(70)
        chv.addWidget(self.ch_notes_edit)

        # Chapter action toolbar — pill-grouped buttons
        def _ch_pill(*pairs):
            """Create a pill-frame containing (label, slot) button pairs."""
            frame = QFrame(); frame.setObjectName("toolGroup")
            fl = QHBoxLayout(frame)
            fl.setContentsMargins(3, 2, 3, 2); fl.setSpacing(1)
            for label, slot in pairs:
                b = QPushButton(label); b.clicked.connect(slot)
                fl.addWidget(b)
            return frame

        ch_save_btn = QPushButton("Save Chapter")
        ch_save_btn.setObjectName("accent")
        ch_save_btn.clicked.connect(self._save_chapter)

        ch_btn_row = QHBoxLayout()
        ch_btn_row.setSpacing(6)
        ch_btn_row.setContentsMargins(0, 4, 0, 0)
        ch_btn_row.addWidget(ch_save_btn)
        ch_btn_row.addWidget(_ch_pill(
            ("Find & Replace", self._open_find_replace),
            ("Word Stats",     self._show_word_stats),
            ("History",        self._show_revision_history),
        ))
        ch_btn_row.addWidget(_ch_pill(
            ("Mentions",       self._scan_character_mentions),
            ("Scene Card",     self._edit_scene_card),
            ("Tension",        self._show_tension_curve),
        ))
        ch_btn_row.addWidget(_ch_pill(
            ("Mood",           self._edit_mood_tags),
            ("Plot Threads",   self._link_plot_threads),
            ("Link Events",    self._link_chapter_events),
            ("Dialogue",       self._extract_dialogue),
            ("Voice",          self._show_voice_profile_panel),
            ("Split",          self._toggle_split_screen),
        ))
        ch_btn_row.addStretch(1)
        chv.addLayout(ch_btn_row)

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
        body = self.ch_body_edit.toPlainText()
        # Save revision snapshot before overwriting
        self.db.save_chapter_revision(self.current_chapter_id, body)
        self.db.update_chapter(
            self.current_chapter_id,
            self.ch_title_edit.text(),
            body,
            self.ch_notes_edit.toPlainText(),
            self.ch_status_combo.currentText(),
        )
        self._reload_chapters(select_id=self.current_chapter_id)
        if self.current_manuscript_id:
            ms = self.db.get_manuscript(self.current_manuscript_id)
            self.ms_word_count_label.setText(f"{ms.get('word_count', 0):,} words")
        self._update_word_goal_bar()
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

    # ------------------------------------------------------------------
    # Spell-check helpers
    # ------------------------------------------------------------------

    def _get_all_lexicon_words(self) -> list[str]:
        """Return all lexicon *words* from every language in the current project."""
        if not self.current_project_id:
            return []
        words = []
        for lang in self.db.list_languages(self.current_project_id):
            for entry in self.db.list_lexicon(lang["id"]):
                w = entry["word"].strip()
                if w:
                    words.append(w)
        return words

    def _on_spell_lang_changed(self, *_):
        """Rebuild spell checker and reattach to the chapter body editor."""
        lang_name = self.spell_lang_combo.currentText()
        if lang_name == "Off":
            self.ch_body_edit.set_spell(None)
            return

        # Lexicon-only mode for constructed languages
        if lang_name.startswith("Lexicon only: "):
            conlang_name = lang_name[len("Lexicon only: "):]
            words = []
            if self.current_project_id:
                for lang in self.db.list_languages(self.current_project_id):
                    if lang["name"] == conlang_name:
                        words = [e["word"].strip() for e in self.db.list_lexicon(lang["id"]) if e["word"].strip()]
                        break
            # Build a checker with ONLY these words (no base language dictionary)
            spell = _build_lexicon_only_checker(words)
            self.ch_body_edit.set_spell(spell)
            return

        lang_code = SPELL_LANGUAGES.get(lang_name, "en")
        extra = []
        if self.spell_lexicon_check.isChecked():
            extra = self._get_all_lexicon_words()
        spell = _build_spell_checker(lang_code, extra)
        if spell is None:
            self.statusBar().showMessage(
                "pyspellchecker not installed — run: pip install pyspellchecker"
            )
        self.ch_body_edit.set_spell(spell)

    def _refresh_spell_lang_combo(self):
        """Add/remove Lexicon-only entries for constructed languages."""
        if not hasattr(self, "spell_lang_combo"):
            return
        combo = self.spell_lang_combo
        # Remove old lexicon-only entries
        for i in range(combo.count() - 1, -1, -1):
            if combo.itemText(i).startswith("Lexicon only: "):
                combo.removeItem(i)
        # Add current project languages
        if self.current_project_id:
            for lang in self.db.list_languages(self.current_project_id):
                combo.addItem(f"Lexicon only: {lang['name']}")

    def _refresh_spell_checker(self):
        """Call after saving a language so new lexicon words are picked up."""
        if not hasattr(self, "spell_lang_combo"):
            return  # UI not yet fully built
        if self.spell_lang_combo.currentText() != "Off":
            self._on_spell_lang_changed()

    # ------------------------------------------------------------------
    # Chapter font helpers
    # ------------------------------------------------------------------

    def _register_font(self, ttf_path: str) -> str | None:
        """Register a TTF with Qt and return its family name, or None on error."""
        font_id = QFontDatabase.addApplicationFont(ttf_path)
        if font_id == -1:
            return None
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            return None
        return families[0]

    def _add_font_to_chapter_combo(self, family: str, ttf_path: str):
        """Add *family* to the chapter font selector if not already present."""
        self._registered_fonts[family] = ttf_path
        # Avoid duplicates
        for i in range(self.ch_font_combo.count()):
            if self.ch_font_combo.itemText(i) == family:
                return
        self.ch_font_combo.addItem(family)

    def _on_chapter_font_changed(self, *_):
        """Apply the selected font/size to the chapter body editor."""
        family = self.ch_font_combo.currentText()
        try:
            size = int(self.ch_font_size_spin.currentText())
        except ValueError:
            size = 12
        if family == "Default":
            self.ch_body_edit.setFont(QApplication.font())
        else:
            font = QFont(family, size)
            self.ch_body_edit.setFont(font)

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

        self.font_use_btn = QPushButton("Use in Manuscript Editor")
        self.font_use_btn.setToolTip("Generate the font and make it available in the chapter editor font selector")
        self.font_use_btn.clicked.connect(self._font_generate_and_use)
        gen_row.addWidget(self.font_use_btn)

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
            # Auto-register the font so it can be used in the chapter editor
            family = self._register_font(ttf_path)
            if family:
                self._add_font_to_chapter_combo(family, ttf_path)
            self.font_status_label.setText(f"✓ Font saved to: {ttf_path}")
            self.statusBar().showMessage(f"Font generated: {os.path.basename(ttf_path)}")
            QMessageBox.information(
                self, "Font Studio",
                f"TTF generated successfully!\n\n{ttf_path}\n\n"
                "The font has been registered and is available in the Manuscript "
                "editor font selector.\nYou can also install it system-wide by "
                "double-clicking the file."
            )
        except Exception as exc:
            self.font_status_label.setText(f"⚠ {exc}")
            QMessageBox.critical(self, "Font Studio — Error", str(exc))
        finally:
            self.font_gen_btn.setEnabled(True)

    def _font_generate_and_use(self):
        """Generate the TTF and immediately apply it in the chapter body editor."""
        self.font_gen_btn.setEnabled(False)
        self.font_use_btn.setEnabled(False)
        self.font_status_label.setText("Generating TTF…")
        QApplication.processEvents()
        try:
            ttf_path = self._font_run_generation()
            family = self._register_font(ttf_path)
            if family:
                self._add_font_to_chapter_combo(family, ttf_path)
                # Switch the chapter editor to use this font right away
                idx = self.ch_font_combo.findText(family)
                if idx >= 0:
                    self.ch_font_combo.setCurrentIndex(idx)
                self.font_status_label.setText(
                    f"✓ Font '{family}' registered and applied to the chapter editor."
                )
                self.statusBar().showMessage(f"Font '{family}' active in chapter editor")
                # Switch to the Manuscripts tab so the user sees the result
                self._switch_to_tab("Manuscripts")
            else:
                self.font_status_label.setText(
                    f"✓ Font saved to: {ttf_path} (could not register — try installing it)"
                )
        except Exception as exc:
            self.font_status_label.setText(f"⚠ {exc}")
            QMessageBox.critical(self, "Font Studio — Error", str(exc))
        finally:
            self.font_gen_btn.setEnabled(True)
            self.font_use_btn.setEnabled(True)

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


    # ==================================================================
    # Tab builders for new features
    # ==================================================================

    def _build_relationship_web_tab(self):
        self.rel_web_widget = RelationshipWebWidget(self.db, None)
        return self.rel_web_widget

    def _build_world_map_tab(self):
        self.world_map_widget = WorldMapWidget(self.db, None)
        return self.world_map_widget

    def _build_name_generator_tab(self):
        self.name_gen_widget = NameGeneratorWidget(self.db, None)
        return self.name_gen_widget

    def _build_plot_threads_tab(self):
        self.plot_thread_widget = PlotThreadWidget(self.db, None)
        return self.plot_thread_widget

    def _build_research_board_tab(self):
        self.research_board_widget = ResearchBoardWidget(self.db, None)
        return self.research_board_widget

    def _build_session_timer_tab(self):
        self.session_timer_widget = SessionTimerWidget(self.db, None)
        self.session_timer_widget.set_word_count_fn(self._count_all_words)
        return self.session_timer_widget

    def _build_world_calendar_tab(self):
        self.world_calendar_widget = WorldCalendarWidget(self.db, None)
        return self.world_calendar_widget

    # ==================================================================
    # Theme toggle
    # ==================================================================

    def _toggle_theme(self):
        if not hasattr(self, '_light_theme'):
            self._light_theme = False
        self._light_theme = not self._light_theme
        QApplication.instance().setStyleSheet(LIGHT_STYLESHEET if self._light_theme else DARK_STYLESHEET)

    # ==================================================================
    # Lore Bible HTML export
    # ==================================================================

    def _export_lore_bible(self):
        if not self._require_project():
            return
        project = self.db.get_project(self.current_project_id)
        slug = safe_slug(project['name'])
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Lore Bible", f"{slug}_lore_bible.html", "HTML (*.html)"
        )
        if not path:
            return
        try:
            export_lore_bible(self.db, self.current_project_id, path)
            QMessageBox.information(self, "Lore Bible",
                f"Exported to:\n{path}\n\nOpen it in any web browser.")
            self.statusBar().showMessage(f"Lore Bible exported: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Lore Bible Export Failed", str(exc))

    # ==================================================================
    # EPUB export
    # ==================================================================

    def _export_epub(self):
        if not self._require_project():
            return
        project = self.db.get_project(self.current_project_id)
        slug = safe_slug(project['name'])
        path, _ = QFileDialog.getSaveFileName(
            self, "Export EPUB", f"{slug}.epub", "EPUB (*.epub)"
        )
        if not path:
            return
        try:
            self._write_epub(project, path)
            QMessageBox.information(self, "EPUB Export", f"Exported to:\n{path}")
            self.statusBar().showMessage(f"EPUB exported: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "EPUB Export Failed", str(exc))

    def _write_epub(self, project, path):
        import zipfile, uuid
        book_id = str(uuid.uuid4())
        manuscripts = self.db.list_manuscripts(self.current_project_id)
        chapters_all = []
        for ms in manuscripts:
            for ch in self.db.list_chapters(ms['id']):
                chapters_all.append({'ms': ms['title'], 'title': ch['title'], 'body': ch['body']})

        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # mimetype (must be first, uncompressed)
            zf.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip')

            # container.xml
            zf.writestr('META-INF/container.xml', '''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>''')

            # Chapter HTML files
            spine_items = []
            manifest_items = []
            for i, ch in enumerate(chapters_all):
                cid = f'ch{i:04d}'
                fname = f'OEBPS/{cid}.xhtml'
                body_html = '\n'.join(f'<p>{_html_esc(p)}</p>' for p in ch['body'].split('\n') if p.strip())
                zf.writestr(fname, f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{_html_esc(ch["title"])}</title>
<style>body{{font-family:Georgia,serif;line-height:1.6;max-width:38em;margin:auto;padding:1em;}}
h1{{font-size:1.4em;}} p{{margin:.6em 0;}}</style>
</head><body>
<h1>{_html_esc(ch["title"])}</h1>
<p><em>{_html_esc(ch["ms"])}</em></p>
{body_html}
</body></html>''')
                manifest_items.append(f'<item id="{cid}" href="{cid}.xhtml" media-type="application/xhtml+xml"/>')
                spine_items.append(f'<itemref idref="{cid}"/>')

            # NCX toc
            nav_points = '\n'.join(
                f'<navPoint id="np{i}" playOrder="{i+1}"><navLabel><text>{_html_esc(ch["title"])}</text></navLabel><content src="ch{i:04d}.xhtml"/></navPoint>'
                for i, ch in enumerate(chapters_all)
            )
            zf.writestr('OEBPS/toc.ncx', f'''<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head><meta name="dtb:uid" content="{book_id}"/></head>
<docTitle><text>{_html_esc(project["name"])}</text></docTitle>
<navMap>{nav_points}</navMap>
</ncx>''')

            # content.opf
            manifest_items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
            zf.writestr('OEBPS/content.opf', f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid" version="2.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>{_html_esc(project["name"])}</dc:title>
  <dc:identifier id="uid">{book_id}</dc:identifier>
  <dc:language>en</dc:language>
</metadata>
<manifest>{''.join(manifest_items)}</manifest>
<spine toc="ncx">{''.join(spine_items)}</spine>
</package>''')

    # ==================================================================
    # Word goal tracker
    # ==================================================================

    def _set_word_goal(self):
        if not self._require_project():
            return
        goal = self.db.get_word_goal(self.current_project_id)
        dlg = QDialog(self)
        dlg.setWindowTitle("Set Word Goals")
        form = QFormLayout(dlg)
        daily_spin = QSpinBox(); daily_spin.setRange(0, 100000); daily_spin.setValue(goal['daily_goal'])
        total_spin = QSpinBox(); total_spin.setRange(0, 10000000); total_spin.setValue(goal['total_goal'])
        form.addRow("Daily word goal:", daily_spin)
        form.addRow("Total word goal:", total_spin)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.db.upsert_word_goal(self.current_project_id, daily_spin.value(), total_spin.value())
            self._update_word_goal_bar()

    def _update_word_goal_bar(self):
        if not hasattr(self, 'word_goal_bar') or not self.current_project_id:
            return
        goal = self.db.get_word_goal(self.current_project_id)
        total = goal.get('total_goal', 80000) or 80000
        # Count all words across all manuscripts
        word_count = 0
        for ms in self.db.list_manuscripts(self.current_project_id):
            for ch in self.db.list_chapters(ms['id']):
                word_count += len(re.findall(r'\b\w+\b', ch.get('body', '')))
        self.word_goal_bar.setMaximum(max(total, 1))
        self.word_goal_bar.setValue(min(word_count, total))

    # ==================================================================
    # Manuscript: Find & Replace
    # ==================================================================

    def _open_find_replace(self):
        if not hasattr(self, 'ch_body_edit'):
            return
        dlg = FindReplaceDialog(self.ch_body_edit, self)
        dlg.show()

    # ==================================================================
    # Manuscript: Word statistics
    # ==================================================================

    def _show_word_stats(self):
        if not hasattr(self, 'ch_body_edit'):
            return
        text = self.ch_body_edit.toPlainText()
        dlg = WordStatsDialog(text, self)
        dlg.exec()

    # ==================================================================
    # Manuscript: Revision history
    # ==================================================================

    def _show_revision_history(self):
        if not self.current_chapter_id:
            QMessageBox.information(self, APP_TITLE, "Select a chapter first.")
            return
        body = self.ch_body_edit.toPlainText()
        dlg = RevisionHistoryDialog(self.db, self.current_chapter_id, body, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and hasattr(dlg, "restored_body"):
            # Save current text as a snapshot before overwriting
            self.db.save_chapter_revision(self.current_chapter_id, body)
            self.ch_body_edit.setPlainText(dlg.restored_body)
            self.statusBar().showMessage("Chapter restored from snapshot — current version saved as a new snapshot.")

    # ==================================================================
    # Manuscript: Character mention tracker
    # ==================================================================

    def _scan_character_mentions(self):
        if not self.current_project_id or not self.current_chapter_id:
            return
        body = self.ch_body_edit.toPlainText()
        chars = self.db.list_characters(self.current_project_id)
        found = []
        for char in chars:
            name = char['name'].strip()
            if name and re.search(r'\b' + re.escape(name) + r'\b', body, re.IGNORECASE):
                count = len(re.findall(r'\b' + re.escape(name) + r'\b', body, re.IGNORECASE))
                found.append((name, count))
        if not found:
            QMessageBox.information(self, "Character Mentions", "No character names found in this chapter.")
            return
        found.sort(key=lambda x: -x[1])
        msg = "Character mentions in this chapter:\n\n"
        msg += "\n".join(f"  {name}: {count}×" for name, count in found)
        QMessageBox.information(self, "Character Mentions", msg)

    # ==================================================================
    # Manuscript: Scene conflict card
    # ==================================================================

    def _edit_scene_card(self):
        if not self.current_chapter_id:
            QMessageBox.information(self, APP_TITLE, "Select a chapter first.")
            return
        card = self.db.get_scene_card(self.current_chapter_id) or {}
        dlg = QDialog(self)
        dlg.setWindowTitle("Scene Card")
        dlg.setMinimumWidth(420)
        form = QFormLayout(dlg)
        goal_edit = QLineEdit(card.get('goal', ''))
        conflict_edit = QLineEdit(card.get('conflict', ''))
        outcome_edit = QLineEdit(card.get('outcome', ''))
        tension_spin = QSpinBox()
        tension_spin.setRange(1, 5)
        tension_spin.setValue(card.get('tension', 3))
        tension_spin.setToolTip("1 = calm, 5 = maximum tension")
        form.addRow("Scene goal:", goal_edit)
        form.addRow("Conflict:", conflict_edit)
        form.addRow("Outcome:", outcome_edit)
        form.addRow("Tension (1–5):", tension_spin)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.db.upsert_scene_card(
                self.current_chapter_id,
                goal_edit.text(), conflict_edit.text(),
                outcome_edit.text(), tension_spin.value()
            )
            self.statusBar().showMessage("Scene card saved.")

    def _show_tension_curve(self):
        if not self.current_manuscript_id:
            QMessageBox.information(self, APP_TITLE, "Select a manuscript first.")
            return
        cards = self.db.list_scene_cards_for_manuscript(self.current_manuscript_id)
        if not cards:
            QMessageBox.information(self, APP_TITLE,
                "No scene cards yet. Add scene cards via the Scene Card button in each chapter.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Tension Curve")
        dlg.setMinimumSize(600, 320)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Tension across chapters (1 = calm, 5 = maximum tension):"))
        canvas = _TensionCanvas(cards, dlg)
        v.addWidget(canvas, 1)
        close_btn = QPushButton("Close"); close_btn.clicked.connect(dlg.accept)
        v.addWidget(close_btn)
        dlg.exec()

    # ==================================================================
    # Manuscript: Split-screen view
    # ==================================================================

    def _toggle_split_screen(self):
        if not hasattr(self, '_split_dialog') or not self._split_dialog:
            self._split_dialog = _SplitScreenDialog(self.db, self.current_project_id, self)
            self._split_dialog.show()
        else:
            self._split_dialog.close()
            self._split_dialog = None

    # ==================================================================
    # Manuscript: Timeline event link
    # ==================================================================

    def _link_chapter_events(self):
        if not self.current_chapter_id or not self.current_project_id:
            QMessageBox.information(self, APP_TITLE, "Select a chapter first.")
            return
        events = self.db.list_events(self.current_project_id)
        if not events:
            QMessageBox.information(self, APP_TITLE, "No events in this project. Add some in the Events tab.")
            return
        linked = {e['id'] for e in self.db.get_chapter_events(self.current_chapter_id)}
        dlg = QDialog(self)
        dlg.setWindowTitle("Link Timeline Events")
        dlg.setMinimumWidth(360)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Check events that occur in this chapter:"))
        checkboxes = []
        for event in events:
            cb = QCheckBox(f"{event['name']} ({event.get('date_label','?')})")
            cb.setChecked(event['id'] in linked)
            v.addWidget(cb)
            checkboxes.append((cb, event['id']))
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = [eid for cb, eid in checkboxes if cb.isChecked()]
            self.db.set_chapter_events(self.current_chapter_id, selected)
            self.statusBar().showMessage(f"Linked {len(selected)} event(s) to this chapter.")

    # ==================================================================
    # Lexicon autocomplete in chapter editor
    # ==================================================================

    def _update_lexicon_completer(self):
        if not hasattr(self, 'ch_body_edit') or not self.current_project_id:
            return
        words = self._get_all_lexicon_words()
        if hasattr(self, '_ch_completer') and self._ch_completer:
            from PyQt6.QtWidgets import QCompleter
            self._ch_completer.model().setStringList(words)
        else:
            from PyQt6.QtWidgets import QCompleter
            from PyQt6.QtCore import QStringListModel
            model = QStringListModel(words)
            self._ch_completer = QCompleter(model, self)
            self._ch_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self._ch_completer.setWidget(self.ch_body_edit)
            self._ch_completer.activated.connect(self._insert_completion)
        self._ch_completion_prefix = ""

    def _insert_completion(self, completion):
        if not hasattr(self, '_ch_completer'):
            return
        tc = self.ch_body_edit.textCursor()
        extra = len(completion) - len(self._ch_completer.completionPrefix())
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.ch_body_edit.setTextCursor(tc)



    # ==================================================================
    # Mood tags
    # ==================================================================

    MOOD_OPTIONS = ["tense", "melancholic", "action-heavy", "quiet", "hopeful",
                    "ominous", "comedic", "romantic", "mysterious", "triumphant",
                    "despairing", "eerie"]

    def _edit_mood_tags(self):
        if not self.current_chapter_id:
            QMessageBox.information(self, APP_TITLE, "Select a chapter first.")
            return
        current = set(self.db.get_chapter_moods(self.current_chapter_id))
        dlg = QDialog(self)
        dlg.setWindowTitle("Mood & Atmosphere Tags")
        dlg.setMinimumWidth(320)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Select the mood(s) for this chapter:"))
        checkboxes = []
        for mood in self.MOOD_OPTIONS:
            cb = QCheckBox(mood)
            cb.setChecked(mood in current)
            v.addWidget(cb)
            checkboxes.append(cb)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = [cb.text() for cb in checkboxes if cb.isChecked()]
            self.db.set_chapter_moods(self.current_chapter_id, selected)
            self.statusBar().showMessage(f"Mood tags saved: {', '.join(selected) or 'none'}")

    # ==================================================================
    # Plot thread linking (from chapter editor)
    # ==================================================================

    def _link_plot_threads(self):
        if not self.current_chapter_id or not self.current_project_id:
            QMessageBox.information(self, APP_TITLE, "Select a chapter first.")
            return
        threads = self.db.list_plot_threads(self.current_project_id)
        if not threads:
            reply = QMessageBox.question(
                self, "Plot Threads",
                "No plot threads yet. Go to the Plot Threads tab to create some first.")
            return
        linked = {t["id"] for t in self.db.get_chapter_plot_threads(self.current_chapter_id)}
        dlg = QDialog(self)
        dlg.setWindowTitle("Link Plot Threads")
        dlg.setMinimumWidth(320)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel("Check threads active in this chapter:"))
        checkboxes = []
        for t in threads:
            cb = QCheckBox(t["name"])
            cb.setChecked(t["id"] in linked)
            lbl_color = t.get("color", "#ffb454")
            cb.setStyleSheet(f"color:{lbl_color};")
            v.addWidget(cb)
            checkboxes.append((cb, t["id"]))
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = [tid for cb, tid in checkboxes if cb.isChecked()]
            self.db.set_chapter_plot_threads(self.current_chapter_id, selected)
            self.statusBar().showMessage(f"Linked {len(selected)} plot thread(s).")
            if hasattr(self, "plot_thread_widget"):
                self.plot_thread_widget._refresh_map()

    # ==================================================================
    # Dialogue extractor
    # ==================================================================

    def _extract_dialogue(self):
        if not self.current_chapter_id:
            QMessageBox.information(self, APP_TITLE, "Select a chapter first.")
            return
        body = self.ch_body_edit.toPlainText()
        # Find text inside double or single quotes
        lines = re.findall(r'["“‘]([^"”’]{2,})["”’]', body)
        if not lines:
            QMessageBox.information(self, APP_TITLE,
                "No dialogue found. Make sure speech is wrapped in quotes.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Extracted Dialogue")
        dlg.setMinimumSize(600, 420)
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(f"{len(lines)} dialogue line(s) found — stripped of prose:"))
        view = QTextEdit()
        view.setReadOnly(True)
        view.setFont(QFont("Georgia", 11))
        view.setPlainText("\n\n".join(f'"{line.strip()}"' for line in lines))
        v.addWidget(view, 1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        v.addWidget(close_btn)
        dlg.exec()

    # ==================================================================
    # Character voice profile (panel from chapter editor)
    # ==================================================================

    def _show_voice_profile_panel(self):
        chars = self.db.list_characters(self.current_project_id) if self.current_project_id else []
        if not chars:
            QMessageBox.information(self, APP_TITLE,
                "No characters in this project yet.")
            return
        char_names = [c["name"] for c in chars]
        char_ids   = [c["id"]   for c in chars]

        dlg = QDialog(self)
        dlg.setWindowTitle("Character Voice Profile")
        dlg.setMinimumSize(500, 480)
        v = QVBoxLayout(dlg)

        char_row = QHBoxLayout()
        char_row.addWidget(QLabel("Character:"))
        char_combo = QComboBox()
        char_combo.addItems(char_names)
        char_row.addWidget(char_combo, 1)
        v.addLayout(char_row)

        form = QFormLayout()
        vocab_edit      = QLineEdit(); vocab_edit.setPlaceholderText("Formal, archaic, slang-heavy, terse...")
        quirks_edit     = QLineEdit(); quirks_edit.setPlaceholderText("Never finishes sentences, over-explains...")
        never_edit      = QLineEdit(); never_edit.setPlaceholderText("Words or phrases this character would never use")
        accent_edit     = QLineEdit(); accent_edit.setPlaceholderText("Regional dialect, dropped letters, rhythm...")
        example_edit    = QTextEdit(); example_edit.setMaximumHeight(80)
        example_edit.setPlaceholderText("Example lines in their voice...")
        form.addRow("Vocabulary style:", vocab_edit)
        form.addRow("Speech quirks:", quirks_edit)
        form.addRow("Never says:", never_edit)
        form.addRow("Accent / dialect:", accent_edit)
        form.addRow("Example lines:", example_edit)
        v.addLayout(form)

        def load_profile(idx):
            cid = char_ids[idx]
            p = self.db.get_voice_profile(cid)
            vocab_edit.setText(p.get("vocabulary",""))
            quirks_edit.setText(p.get("speech_quirks",""))
            never_edit.setText(p.get("never_says",""))
            accent_edit.setText(p.get("accent_notes",""))
            example_edit.setPlainText(p.get("example_lines",""))

        char_combo.currentIndexChanged.connect(load_profile)
        load_profile(0)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close)
        def save():
            cid = char_ids[char_combo.currentIndex()]
            self.db.upsert_voice_profile(
                cid, vocab_edit.text(), quirks_edit.text(),
                never_edit.text(), accent_edit.text(), example_edit.toPlainText())
            self.statusBar().showMessage("Voice profile saved.")
        btns.accepted.connect(save)
        btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        dlg.exec()

    # ==================================================================
    # Word count helper (for session timer)
    # ==================================================================

    def _count_all_words(self):
        if not self.current_project_id:
            return 0
        total = 0
        for ms in self.db.list_manuscripts(self.current_project_id):
            for ch in self.db.list_chapters(ms["id"]):
                total += len(re.findall(r"\b\w+\b", ch.get("body", "")))
        return total



    # ==================================================================
    # Chapter Templates
    # ==================================================================

    CHAPTER_TEMPLATES = {
        "Three-Act Structure": (
            "[SETUP]\n"
            "Establish the setting, characters present, and the status quo.\n\n"
            "[CONFRONTATION]\n"
            "Introduce the conflict or complication. Raise the stakes.\n\n"
            "[RESOLUTION]\n"
            "Resolve the immediate conflict. End on a hook or consequence."
        ),
        "Scene / Sequel": (
            "[SCENE]\n"
            "Goal: What does the POV character want?\n"
            "Conflict: What opposes them?\n"
            "Disaster: How does the scene end badly or unexpectedly?\n\n"
            "[SEQUEL]\n"
            "Reaction: Emotional response to the disaster.\n"
            "Dilemma: The impossible choice that follows.\n"
            "Decision: What does the character decide to do next?"
        ),
        "In Medias Res": (
            "[ACTION OPENING]\n"
            "Drop the reader into the middle of an event. No preamble.\n\n"
            "[CONTEXT]\n"
            "Weave in just enough backstory to orient the reader.\n\n"
            "[ESCALATION]\n"
            "Push toward the chapter's main conflict or revelation."
        ),
        "Revelation Chapter": (
            "[BEFORE]\n"
            "The character's understanding of the situation so far.\n\n"
            "[THE TURN]\n"
            "The moment of revelation or discovery.\n\n"
            "[AFTER]\n"
            "How this changes everything. Immediate consequences."
        ),
        "Quiet Chapter": (
            "[BREATHING ROOM]\n"
            "A chapter with lower external tension. Focus on character.\n\n"
            "[RELATIONSHIP BEAT]\n"
            "A meaningful exchange or moment between characters.\n\n"
            "[FORESHADOWING]\n"
            "Seed something that will matter later. Keep it subtle."
        ),
    }

    def _new_chapter_from_template(self):
        if not self.current_manuscript_id:
            QMessageBox.information(self, APP_TITLE, "Select a manuscript first.")
            return
        template_names = list(self.CHAPTER_TEMPLATES.keys())
        name, ok = QInputDialog.getItem(
            self, "Chapter Template", "Choose a template:", template_names, editable=False)
        if not ok:
            return
        title, ok2 = QInputDialog.getText(self, "Chapter Title", "Chapter title:")
        if not ok2 or not title.strip():
            return
        body = self.CHAPTER_TEMPLATES[name]
        chapters = self.db.list_chapters(self.current_manuscript_id)
        next_num = max((c["chapter_number"] for c in chapters), default=0) + 1
        ch_id = self.db.create_chapter(
            self.current_manuscript_id, title.strip(), next_num)
        self.db.update_chapter(ch_id, title.strip(), body, "", "Draft")
        self._reload_chapters(select_id=ch_id)
        self.statusBar().showMessage(f"Chapter '{title.strip()}' created from {name} template.")

    # ==================================================================
    # Contradiction Detector
    # ==================================================================

    def _run_contradiction_detector(self):
        if not self.current_project_id:
            QMessageBox.information(self, APP_TITLE, "Select a project first.")
            return
        warnings = []
        chars = self.db.list_characters(self.current_project_id)
        char_names = [c["name"].strip() for c in chars if c["name"].strip()]

        all_chapters = []
        for ms in self.db.list_manuscripts(self.current_project_id):
            for ch in self.db.list_chapters(ms["id"]):
                all_chapters.append({
                    "ms": ms["title"], "ch": ch["title"],
                    "num": ch["chapter_number"], "body": ch.get("body","")
                })

        # Check 1: character appears in many chapters — flag duplicate name variants
        name_variants: dict[str, list[str]] = {}
        for name in char_names:
            parts = name.split()
            if len(parts) > 1:
                for part in parts:
                    if len(part) > 2:
                        name_variants.setdefault(part.lower(), []).append(name)
        for key, names in name_variants.items():
            if len(names) > 1:
                warnings.append(
                    f"Name ambiguity: '{key}' matches multiple characters: {', '.join(names)}"
                )

        # Check 2: chapter references a character name before that character's
        # first appearance in chapter order (simple first-mention check)
        first_seen: dict[str, int] = {}
        for ch in sorted(all_chapters, key=lambda c: c["num"]):
            body_lower = ch["body"].lower()
            for name in char_names:
                if name.lower() in body_lower:
                    if name not in first_seen:
                        first_seen[name] = ch["num"]

        # Check 3: location names mentioned in chapters but not in locations DB
        locations = self.db.list_locations(self.current_project_id)
        loc_names = [l["name"].strip().lower() for l in locations if l["name"].strip()]
        all_body = " ".join(ch["body"] for ch in all_chapters).lower()
        for loc in loc_names:
            if loc and loc not in all_body:
                warnings.append(
                    f"Location '{loc.title()}' is defined but never mentioned in any chapter."
                )

        # Check 4: very short chapters (possibly placeholders)
        for ch in all_chapters:
            wc = len(re.findall(r"\b\w+\b", ch["body"]))
            if 0 < wc < 50:
                warnings.append(
                    f"Short chapter: '{ch['ch']}' ({ch['ms']}) has only {wc} words — may be a placeholder."
                )

        # Check 5: duplicate chapter titles within same manuscript
        seen_titles: dict[str, str] = {}
        for ch in all_chapters:
            key = f"{ch['ms']}::{ch['ch'].strip().lower()}"
            if key in seen_titles:
                warnings.append(
                    f"Duplicate chapter title: '{ch['ch']}' appears more than once in '{ch['ms']}'."
                )
            seen_titles[key] = ch["ch"]

        dlg = QDialog(self)
        dlg.setWindowTitle("Contradiction Detector")
        dlg.setMinimumSize(680, 440)
        v = QVBoxLayout(dlg)
        if warnings:
            v.addWidget(QLabel(f"{len(warnings)} potential issue(s) found:"))
            warn_list = QListWidget()
            warn_list.setAlternatingRowColors(True)
            warn_list.setWordWrap(True)
            for w in warnings:
                warn_list.addItem(QListWidgetItem(w))
            v.addWidget(warn_list, 1)
        else:
            lbl = QLabel("No contradictions or issues detected.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size:15px;color:#5fad56;padding:20px;")
            v.addWidget(lbl)
        note = QLabel("Note: this is a heuristic check, not a full AI analysis. Review each warning manually.")
        note.setObjectName("statusHint")
        note.setWordWrap(True)
        v.addWidget(note)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        v.addWidget(close_btn)
        dlg.exec()

    # ==================================================================
    # Creature stat block save/load hooks
    # ==================================================================

    def _get_creature_stat_fields(self):
        """Return stat block fields as a dict for saving in creature notes."""
        if not hasattr(self, "crt_threat_combo"):
            return {}
        return {
            "__threat__":    self.crt_threat_combo.currentText(),
            "__speed__":     self.crt_speed_edit.text(),
            "__senses__":    self.crt_senses_edit.text(),
            "__languages__": self.crt_lang_edit.text(),
            "__drops__":     self.crt_drops_edit.text(),
            "__encounter__": self.crt_encounter_edit.toPlainText(),
        }

    def _load_creature_stat_fields(self, notes_text: str):
        """Parse stat block fields out of notes and populate the form."""
        if not hasattr(self, "crt_threat_combo"):
            return
        try:
            data = json.loads(notes_text)
            idx = self.crt_threat_combo.findText(data.get("__threat__",""))
            if idx >= 0:
                self.crt_threat_combo.setCurrentIndex(idx)
            self.crt_speed_edit.setText(data.get("__speed__",""))
            self.crt_senses_edit.setText(data.get("__senses__",""))
            self.crt_lang_edit.setText(data.get("__languages__",""))
            self.crt_drops_edit.setText(data.get("__drops__",""))
            self.crt_encounter_edit.setPlainText(data.get("__encounter__",""))
        except (json.JSONDecodeError, TypeError):
            pass


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
        # Refresh new feature widgets
        pid = self.current_project_id
        if hasattr(self, 'rel_web_widget'):
            self.rel_web_widget.project_id = pid
            self.rel_web_widget.refresh()
        if hasattr(self, 'world_map_widget'):
            self.world_map_widget.project_id = pid
            self.world_map_widget.refresh()
        if hasattr(self, 'name_gen_widget'):
            self.name_gen_widget.project_id = pid
            self.name_gen_widget.refresh()
        if hasattr(self, 'plot_thread_widget'):
            self.plot_thread_widget.refresh(project_id=pid)
        if hasattr(self, 'research_board_widget'):
            self.research_board_widget.refresh(project_id=pid)
        if hasattr(self, 'session_timer_widget'):
            self.session_timer_widget.refresh(project_id=pid)
        if hasattr(self, 'world_calendar_widget'):
            self.world_calendar_widget.refresh(project_id=pid)
        self._update_word_goal_bar()
        self._update_lexicon_completer()
        self._refresh_spell_lang_combo()
        if pid is not None:
            project = self.db.get_project(pid)
            self.statusBar().showMessage(f"Active project: {project['name']}")
        else:
            self.statusBar().showMessage("No project selected.")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)

    # Resolve base dir for both normal script and PyInstaller frozen exe
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    from PyQt6.QtGui import QIcon
    icon_path = os.path.join(base_dir, "storyforge_transparent.ico")
    app_icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()
    app.setWindowIcon(app_icon)   # taskbar button icon

    db = Database()
    window = MainWindow(db)
    window.setWindowIcon(app_icon)  # window title-bar corner icon
    window.show()
    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
