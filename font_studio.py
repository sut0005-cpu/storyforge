"""
font_studio.py
--------------
FontStudioConverter — convert a folder of PNG glyph images into a TTF font.

Expected PNG naming convention (case-insensitive):
  A.png  B.png  ...  Z.png          → uppercase letters
  a.png  a_.png  a_lower.png        → lowercase letters (any suffix works)
  0.png  1.png  ...  9.png          → digits
  space.png  exclaim.png  period.png → punctuation helpers (optional)

Any PNG whose stem is a single ASCII character is mapped directly.
PNGs with a two-character stem are also tried (e.g. "a_" → 'a').

Requires:  pip install fonttools Pillow
"""

import os
import re
import struct
import time
from pathlib import Path

# ── optional deps — fail loudly only when actually called ──────────────────

def _require(package: str, import_name: str):
    try:
        return __import__(import_name)
    except ImportError:
        raise ImportError(
            f"'{package}' is required for font generation.\n"
            f"Install it with:  pip install {package}"
        )


# ── Unicode helpers ────────────────────────────────────────────────────────

_STEM_TO_CODEPOINT: dict[str, int] = {
    # digits
    **{str(d): ord(str(d)) for d in range(10)},
    # uppercase
    **{chr(c): c for c in range(ord("A"), ord("Z") + 1)},
    # lowercase
    **{chr(c): c for c in range(ord("a"), ord("z") + 1)},
    # common punctuation by name
    "space": 0x20,
    "exclaim": 0x21,
    "exclamation": 0x21,
    "quote": 0x22,
    "hash": 0x23,
    "dollar": 0x24,
    "percent": 0x25,
    "ampersand": 0x26,
    "apostrophe": 0x27,
    "lparen": 0x28,
    "rparen": 0x29,
    "asterisk": 0x2A,
    "plus": 0x2B,
    "comma": 0x2C,
    "minus": 0x2D,
    "hyphen": 0x2D,
    "period": 0x2E,
    "dot": 0x2E,
    "slash": 0x2F,
    "colon": 0x3A,
    "semicolon": 0x3B,
    "lt": 0x3C,
    "equal": 0x3D,
    "gt": 0x3E,
    "question": 0x3F,
    "at": 0x40,
    "lbracket": 0x5B,
    "backslash": 0x5C,
    "rbracket": 0x5D,
    "caret": 0x5E,
    "underscore": 0x5F,
    "backtick": 0x60,
    "lbrace": 0x7B,
    "pipe": 0x7C,
    "rbrace": 0x7D,
    "tilde": 0x7E,
}


def _stem_to_codepoint(stem: str) -> int | None:
    """Return the Unicode codepoint for a PNG file stem, or None if unknown."""
    s = stem.strip()
    # direct single-char match
    if len(s) == 1:
        return ord(s)
    # dict lookup (case-sensitive first, then lowercase)
    if s in _STEM_TO_CODEPOINT:
        return _STEM_TO_CODEPOINT[s]
    if s.lower() in _STEM_TO_CODEPOINT:
        return _STEM_TO_CODEPOINT[s.lower()]
    # "A_lower" / "a_" style — strip trailing non-alpha and retry
    base = re.sub(r"[^A-Za-z0-9].*$", "", s)
    if base in _STEM_TO_CODEPOINT:
        return _STEM_TO_CODEPOINT[base]
    if base.lower() in _STEM_TO_CODEPOINT:
        return _STEM_TO_CODEPOINT[base.lower()]
    return None


# ── PNG → contours via fonttools ───────────────────────────────────────────

def _png_to_glyph(png_path: str, em: int = 1000, baseline_ratio: float = 0.2):
    """
    Rasterise a PNG glyph image and trace it into fonttools pen commands.

    Returns (contours, advance_width) where contours is a list of
    [(x,y), ...] point lists (closed polygons in font coordinates).
    """
    Image = _require("Pillow", "PIL.Image").Image  # type: ignore
    from PIL import Image  # noqa: F811

    img = Image.open(png_path).convert("RGBA")
    w, h = img.size

    # Scale so the cap height = em * (1 - baseline_ratio)
    cap_height = em * (1 - baseline_ratio)
    scale = cap_height / h if h else 1.0
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Convert alpha channel to a binary mask
    alpha = img.split()[3]
    threshold = 128
    mask = alpha.point(lambda p: 255 if p >= threshold else 0, "1")

    # Trace outlines using potrace-style marching squares (simplified)
    # We use fonttools' PointToSegmentPen + a simple contour tracer
    pixels = mask.load()
    visited = [[False] * new_w for _ in range(new_h)]
    contours = []

    def _trace(start_r, start_c):
        """Flood-fill boundary trace — returns pixel boundary polygon."""
        # directions: right, down, left, up
        dr = [0, 1, 0, -1]
        dc = [1, 0, -1, 0]
        path = []
        r, c = start_r, start_c
        direction = 0
        for _ in range(new_w * new_h * 4):
            path.append((c, new_h - r))  # flip y for font coordinates
            visited[r][c] = True
            # Try to turn left first (keeps boundary tight)
            left_dir = (direction - 1) % 4
            nr, nc = r + dr[left_dir], c + dc[left_dir]
            if 0 <= nr < new_h and 0 <= nc < new_w and pixels[nc, nr] and not visited[nr][nc]:
                direction = left_dir
                r, c = nr, nc
            else:
                # Try straight
                nr, nc = r + dr[direction], c + dc[direction]
                if 0 <= nr < new_h and 0 <= nc < new_w and pixels[nc, nr]:
                    r, c = nr, nc
                else:
                    # Turn right
                    direction = (direction + 1) % 4
                    nr, nc = r + dr[direction], c + dc[direction]
                    if 0 <= nr < new_h and 0 <= nc < new_w and pixels[nc, nr]:
                        r, c = nr, nc
                    else:
                        break
            if (r, c) == (start_r, start_c):
                break
        return path

    for row in range(new_h):
        for col in range(new_w):
            if pixels[col, row] and not visited[row][col]:
                contour = _trace(row, col)
                if len(contour) >= 3:
                    # Shift y up by baseline offset
                    baseline_px = round(em * baseline_ratio)
                    shifted = [(x + 0, y + baseline_px) for x, y in contour]
                    contours.append(shifted)

    advance_width = round(new_w + em * 0.1)  # glyph width + 10% side-bearing
    return contours, advance_width


# ── Main converter class ───────────────────────────────────────────────────

class FontStudioConverter:
    """
    Convert a folder of PNG glyph images into a TTF font file.

    Usage::

        fsc = FontStudioConverter()
        output_path = fsc.create_ttf_from_pngs(
            png_folder="user_glyphs/",
            output_name="MyCustomFont",
        )
        print(f"Font saved to {output_path}")
    """

    EM = 1000          # units per em
    ASCENDER = 800
    DESCENDER = -200
    LINE_GAP = 0

    def create_ttf_from_pngs(
        self,
        png_folder: str,
        output_name: str = "CustomFont",
        output_dir: str | None = None,
    ) -> str:
        """
        Build a TTF from the PNG files found in *png_folder*.

        Parameters
        ----------
        png_folder : str
            Path to the folder containing glyph PNGs.
        output_name : str
            Base name for the output TTF (no extension).
        output_dir : str | None
            Where to write the TTF.  Defaults to *png_folder*.

        Returns
        -------
        str
            Absolute path to the generated .ttf file.
        """
        # ── resolve paths ──────────────────────────────────────────────
        png_folder = os.path.abspath(png_folder)
        if not os.path.isdir(png_folder):
            raise FileNotFoundError(f"PNG folder not found: {png_folder}")

        if output_dir is None:
            output_dir = png_folder
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{output_name}.ttf")

        # ── collect PNGs ───────────────────────────────────────────────
        png_files = sorted(
            p for p in Path(png_folder).iterdir()
            if p.suffix.lower() == ".png"
        )
        if not png_files:
            raise ValueError(f"No PNG files found in {png_folder}")

        # ── import fonttools ───────────────────────────────────────────
        try:
            from fontTools.fontBuilder import FontBuilder  # type: ignore
            from fontTools.pens.t2Pen import T2Pen  # type: ignore
            from fontTools.ttLib import TTFont  # type: ignore
        except ImportError:
            raise ImportError(
                "fonttools is required for TTF generation.\n"
                "Install it with:  pip install fonttools"
            )

        # ── build glyph map ────────────────────────────────────────────
        glyph_map: dict[int, tuple] = {}   # codepoint → (contours, adv)
        skipped = []

        for png_path in png_files:
            stem = png_path.stem
            cp = _stem_to_codepoint(stem)
            if cp is None:
                skipped.append(png_path.name)
                continue
            try:
                contours, adv = _png_to_glyph(str(png_path), em=self.EM)
                glyph_map[cp] = (contours, adv)
            except Exception as exc:
                skipped.append(f"{png_path.name} ({exc})")

        if not glyph_map:
            raise ValueError(
                "No glyphs could be built. "
                f"Skipped files: {skipped or 'none'}"
            )

        # ── assemble TTF with FontBuilder ──────────────────────────────
        fb = FontBuilder(self.EM, isTTF=True)

        # Required glyph names
        glyph_order = [".notdef"] + [
            f"uni{cp:04X}" for cp in sorted(glyph_map)
        ]
        fb.setupGlyphOrder(glyph_order)

        # cmap: Unicode → glyph name
        cmap = {cp: f"uni{cp:04X}" for cp in glyph_map}
        fb.setupCharacterMap(cmap)

        # glyph metrics
        metrics = {".notdef": (500, 0)}
        for cp, (_, adv) in glyph_map.items():
            metrics[f"uni{cp:04X}"] = (adv, 0)
        fb.setupHorizontalMetrics(metrics)

        # Draw glyphs using the simple pen interface
        pen_class = fb.setupGlyf({})  # initialise glyf table
        # We'll draw directly via the glyf table
        from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph  # type: ignore
        import array

        glyf_table = fb.font["glyf"]

        # .notdef — simple empty box
        notdef = TTGlyph()
        notdef.numberOfContours = 1
        notdef.coordinates = _make_array([(50, 0), (450, 0), (450, 700), (50, 700)])
        notdef.flags = array.array("B", [1, 1, 1, 1])
        notdef.endPtsOfContours = [3]
        notdef.program = None
        glyf_table[".notdef"] = notdef

        for cp, (contours, _adv) in glyph_map.items():
            gname = f"uni{cp:04X}"
            g = TTGlyph()
            if not contours:
                g.numberOfContours = 0
                g.coordinates = _make_array([])
                g.flags = array.array("B", [])
                g.endPtsOfContours = []
            else:
                all_pts: list[tuple[int, int]] = []
                end_pts: list[int] = []
                for contour in contours:
                    all_pts.extend([(int(x), int(y)) for x, y in contour])
                    end_pts.append(len(all_pts) - 1)
                g.numberOfContours = len(contours)
                g.coordinates = _make_array(all_pts)
                g.flags = array.array("B", [1] * len(all_pts))
                g.endPtsOfContours = end_pts
            g.program = None
            glyf_table[gname] = g

        # name table
        fb.setupNameTable({
            "familyName": output_name,
            "styleName": "Regular",
        })

        # head / hhea / OS/2 / post
        fb.setupHead(unitsPerEm=self.EM)
        fb.setupHorizontalHeader(
            ascent=self.ASCENDER, descent=self.DESCENDER
        )
        fb.setupOs2(
            sTypoAscender=self.ASCENDER,
            sTypoDescender=self.DESCENDER,
            sTypoLineGap=self.LINE_GAP,
            usWinAscent=self.ASCENDER,
            usWinDescent=abs(self.DESCENDER),
        )
        fb.setupPost()

        fb.font.save(output_path)
        return output_path


# ── helpers ────────────────────────────────────────────────────────────────

def _make_array(pts):
    """Return a fontTools-compatible coordinate array."""
    try:
        from fontTools.misc.arrayTools import (  # type: ignore
            unionRect,
        )
        from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates  # type: ignore
        return GlyphCoordinates(pts)
    except ImportError:
        # Fall back to plain list — fontTools accepts both
        return list(pts)
