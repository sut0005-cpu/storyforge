"""
docx_export.py
StoryForge — Export every section of a project to separate .docx files
bundled in a single .zip archive.

Sections exported:
  - Manuscripts (one .docx per manuscript, with chapters)
  - Characters
  - Locations
  - Events
  - Creatures
  - Magic Systems
  - Religions
  - Timeline (Eras)
  - Languages (with lexicon table)
"""

import io
import os
import re
import zipfile

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _safe_filename(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    slug = re.sub(r"[\s]+", "_", slug.strip())
    return slug or "untitled"


def _new_doc() -> Document:
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1.25)
        section.right_margin  = Inches(1.25)
    return doc


def _doc_title(doc: Document, title: str, subtitle: str = ""):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title)
    r.bold = True
    r.font.size = Pt(22)
    r.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
    p.paragraph_format.space_after = Pt(2)
    if subtitle:
        sp = doc.add_paragraph()
        sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sr = sp.add_run(subtitle)
        sr.italic = True
        sr.font.size = Pt(11)
        sr.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        sp.paragraph_format.space_after = Pt(12)
    else:
        p.paragraph_format.space_after = Pt(12)


def _section_heading(doc: Document, text: str, level: int = 1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 8)
    p.paragraph_format.space_after  = Pt(4)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(15 if level == 1 else 12)
    r.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)


def _field(doc: Document, label: str, value: str):
    if not (value and value.strip()):
        return
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    lr = p.add_run(f"{label}: ")
    lr.bold = True
    lr.font.size = Pt(11)
    vr = p.add_run(value)
    vr.font.size = Pt(11)


def _body_text(doc: Document, text: str):
    if not (text and text.strip()):
        return
    for line in text.split("\n"):
        p = doc.add_paragraph(line)
        p.paragraph_format.space_after = Pt(0)
        if p.runs:
            p.runs[0].font.size = Pt(11)


def _divider(doc: Document):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(6)
    r = p.add_run("─" * 55)
    r.font.size = Pt(7)
    r.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)


def _to_bytes(doc: Document) -> bytes:
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_manuscripts(db, project_id: int) -> list[tuple[str, bytes]]:
    """One .docx per manuscript."""
    results = []
    for ms in db.list_manuscripts(project_id):
        doc = _new_doc()
        _doc_title(doc, ms["title"], f"{ms.get('genre','')}  ·  {ms.get('status','')}")
        _field(doc, "Word count", f"{ms.get('word_count', 0):,}")
        synopsis = (ms.get("synopsis") or "").strip()
        if synopsis:
            _section_heading(doc, "Synopsis", 2)
            _body_text(doc, synopsis)

        chapters = db.list_chapters(ms["id"])
        for ch in chapters:
            _divider(doc)
            ch_num   = ch.get("chapter_number", "")
            ch_title = (ch.get("title") or "").strip()
            heading  = f"Chapter {ch_num}" + (f": {ch_title}" if ch_title else "")
            _section_heading(doc, heading)
            _body_text(doc, ch.get("body") or "")
            notes = (ch.get("notes") or "").strip()
            if notes:
                _field(doc, "Notes", notes)

        fname = f"manuscript_{_safe_filename(ms['title'])}.docx"
        results.append((fname, _to_bytes(doc)))
    return results


def _build_characters(db, project_id: int) -> tuple[str, bytes] | None:
    chars = db.list_characters(project_id)
    if not chars:
        return None
    doc = _new_doc()
    _doc_title(doc, "Characters")
    for i, c in enumerate(chars):
        if i:
            _divider(doc)
        _section_heading(doc, c["name"])
        _field(doc, "Role", c.get("role") or "")
        _body_text(doc, c.get("bio") or "")
        for key, val in db.get_character_attributes(c["id"]):
            _field(doc, key, val)
    return ("characters.docx", _to_bytes(doc))


def _build_locations(db, project_id: int) -> tuple[str, bytes] | None:
    locs = db.list_locations(project_id)
    if not locs:
        return None
    doc = _new_doc()
    _doc_title(doc, "Locations")
    for i, loc in enumerate(locs):
        if i:
            _divider(doc)
        _section_heading(doc, loc["name"])
        _field(doc, "Type",       loc.get("type") or "")
        _field(doc, "Climate",    loc.get("climate") or "")
        _field(doc, "Population", loc.get("population") or "")
        _body_text(doc, loc.get("description") or "")
        _field(doc, "Notes",      loc.get("notes") or "")
        for key, val in db.get_location_attributes(loc["id"]):
            _field(doc, key, val)
    return ("locations.docx", _to_bytes(doc))


def _build_events(db, project_id: int) -> tuple[str, bytes] | None:
    evts = db.list_events(project_id)
    if not evts:
        return None
    doc = _new_doc()
    _doc_title(doc, "Events")

    # Build location id→name lookup
    loc_map = {l["id"]: l["name"] for l in db.list_locations(project_id)}

    for i, evt in enumerate(evts):
        if i:
            _divider(doc)
        title = evt.get("title", "Untitled")
        date  = evt.get("date_label") or ""
        _section_heading(doc, f"{date}  {title}" if date else title)
        _field(doc, "Type",     evt.get("event_type") or "")
        loc_id = evt.get("location_id")
        if loc_id and loc_id in loc_map:
            _field(doc, "Location", loc_map[loc_id])
        _body_text(doc, evt.get("description") or "")
        _field(doc, "Notes", evt.get("notes") or "")
        linked = [c["name"] for c in db.get_event_characters(evt["id"])]
        if linked:
            _field(doc, "Characters", ", ".join(linked))
    return ("events.docx", _to_bytes(doc))


def _build_creatures(db, project_id: int) -> tuple[str, bytes] | None:
    creatures = db.list_creatures(project_id)
    if not creatures:
        return None
    doc = _new_doc()
    _doc_title(doc, "Creatures & Beasts")
    for i, c in enumerate(creatures):
        if i:
            _divider(doc)
        _section_heading(doc, c["name"])
        _field(doc, "Type",    c.get("creature_type") or "")
        _field(doc, "Habitat", c.get("habitat") or "")
        _field(doc, "Size",    c.get("size") or "")
        _field(doc, "Diet",    c.get("diet") or "")
        _body_text(doc, c.get("behaviour") or "")
        _field(doc, "Abilities",  c.get("abilities") or "")
        _field(doc, "Weaknesses", c.get("weaknesses") or "")
        _body_text(doc, c.get("lore") or "")
        _field(doc, "Notes", c.get("notes") or "")
    return ("creatures.docx", _to_bytes(doc))


def _build_magic_systems(db, project_id: int) -> tuple[str, bytes] | None:
    systems = db.list_magic_systems(project_id)
    if not systems:
        return None
    doc = _new_doc()
    _doc_title(doc, "Magic Systems")
    for i, ms in enumerate(systems):
        if i:
            _divider(doc)
        _section_heading(doc, ms["name"])
        _field(doc, "Classification", ms.get("classification") or "")
        _field(doc, "Source",         ms.get("source") or "")
        _body_text(doc, ms.get("description") or "")
        _field(doc, "Rules",       ms.get("rules") or "")
        _field(doc, "Limitations", ms.get("limitations") or "")
        _field(doc, "Cost",        ms.get("cost") or "")
        abilities = db.list_magic_abilities(ms["id"])
        if abilities:
            _section_heading(doc, "Abilities", 2)
            for ab in abilities:
                _field(doc, ab["name"], f"[Tier {ab['tier']}] {ab['description']}")
    return ("magic_systems.docx", _to_bytes(doc))


def _build_religions(db, project_id: int) -> tuple[str, bytes] | None:
    religions = db.list_religions(project_id)
    if not religions:
        return None
    doc = _new_doc()
    _doc_title(doc, "Religions & Faiths")
    for i, rel in enumerate(religions):
        if i:
            _divider(doc)
        _section_heading(doc, rel["name"])
        _field(doc, "Pantheon Type", rel.get("pantheon_type") or "")
        _body_text(doc, rel.get("description") or "")
        _field(doc, "Beliefs",        rel.get("beliefs") or "")
        _field(doc, "Practices",      rel.get("practices") or "")
        _field(doc, "Holy Texts",     rel.get("holy_texts") or "")
        _field(doc, "Afterlife Views",rel.get("afterlife_views") or "")
        deities = db.list_religion_deities(rel["id"])
        if deities:
            _section_heading(doc, "Deities", 2)
            for d in deities:
                _field(doc, d["name"], f"({d['domain']}) {d['description']}")
    return ("religions.docx", _to_bytes(doc))


def _build_timeline(db, project_id: int) -> tuple[str, bytes] | None:
    eras = db.list_eras(project_id)
    if not eras:
        return None
    doc = _new_doc()
    _doc_title(doc, "Timeline")
    for i, era in enumerate(eras):
        if i:
            _divider(doc)
        span = ""
        if era.get("start_label") or era.get("end_label"):
            span = f"{era.get('start_label','')} – {era.get('end_label','')}"
        _section_heading(doc, f"{era['name']}{' (' + span + ')' if span else ''}")
        _body_text(doc, era.get("description") or "")
    return ("timeline.docx", _to_bytes(doc))


def _build_languages(db, project_id: int) -> tuple[str, bytes] | None:
    langs = db.list_languages(project_id)
    if not langs:
        return None
    doc = _new_doc()
    _doc_title(doc, "Languages")
    for i, lang in enumerate(langs):
        if i:
            _divider(doc)
        _section_heading(doc, lang["name"])
        _body_text(doc, lang.get("grammar") or "")

        lexicon = db.list_lexicon(lang["id"])
        if lexicon:
            _section_heading(doc, "Lexicon", 2)
            from docx.oxml.ns import qn
            from docx.oxml import OxmlElement

            table = doc.add_table(rows=1, cols=4)
            table.style = "Table Grid"
            hdr = table.rows[0].cells
            for idx, label in enumerate(["Word", "Translation", "Part of Speech", "Notes"]):
                p = hdr[idx].paragraphs[0]
                r = p.add_run(label)
                r.bold = True
                r.font.size = Pt(10)
            for entry in lexicon:
                row = table.add_row().cells
                for idx, val in enumerate([
                    entry.get("word", ""),
                    entry.get("translation", ""),
                    entry.get("part_of_speech", ""),
                    entry.get("notes", ""),
                ]):
                    p = row[idx].paragraphs[0]
                    r = p.add_run(val or "")
                    r.font.size = Pt(10)
            doc.add_paragraph()  # spacing after table
    return ("languages.docx", _to_bytes(doc))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def export_sections_to_zip(db, project_id: int, project_name: str, dest_zip: str) -> list:
    """
    Export every section with data into one zip.

    Returns list of filenames written into the zip.
    """
    outputs: list[tuple[str, bytes]] = []

    # Manuscripts: one file each
    outputs.extend(_build_manuscripts(db, project_id))

    # Single-file sections
    for builder in [
        _build_characters,
        _build_locations,
        _build_events,
        _build_creatures,
        _build_magic_systems,
        _build_religions,
        _build_timeline,
        _build_languages,
    ]:
        result = builder(db, project_id)
        if result:
            outputs.append(result)

    if not outputs:
        raise ValueError("This project has no content to export.")

    # Deduplicate filenames
    seen: dict[str, int] = {}
    deduped = []
    for fname, data in outputs:
        if fname in seen:
            seen[fname] += 1
            base, ext = os.path.splitext(fname)
            fname = f"{base}_{seen[fname]}{ext}"
        else:
            seen[fname] = 0
        deduped.append((fname, data))

    with zipfile.ZipFile(dest_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname, data in deduped:
            zf.writestr(fname, data)

    return [fname for fname, _ in deduped]
