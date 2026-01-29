import re
from typing import Optional, List
import discord


# Glyph mapping (stub)
#
GLYPH_MAP = {
    "portal0": "0", "portal1": "1", "portal2": "2", "portal3": "3",
    "portal4": "4", "portal5": "5", "portal6": "6", "portal7": "7",
    "portal8": "8", "portal9": "9", "portala": "A", "portalb": "B",
    "portalc": "C", "portald": "D", "portale": "E", "portalf": "F",
}

# -----------------------------
# Normalization helpers
# -----------------------------
def normalize_line(line: Optional[str]) -> str:
    if line is None:
        return ""
    clean = line.replace("`", "")
    clean = clean.replace("“", '"').replace("”", '"')
    clean = clean.replace("–", "-").replace("—", "-")
    clean = re.sub(r"^[\s\-\*\•\u2022\u2023\u25E6\u2027\•\t]+", "", clean)
    clean = re.sub(r"[\u200B-\u200F\uFEFF]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def line_contains_field(line: str, field_label: str) -> bool:
    if not line:
        return False
    return field_label.lower() in line.lower()

def extract_after_colon(line: Optional[str]) -> str:
    if not line:
        return ""
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return ""

def clean_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.rstrip(", ").strip()

def strip_emojis(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    return re.sub(r"<a?:\w+:\d+>", "", text).strip()

def normalize_key(label: str) -> str:
    if not label:
        return label
    s = re.sub(r"[^\w\s-]", "", label)
    s = s.strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    return s

# -----------------------------
# Glyph extraction
# -----------------------------
def glyphs_to_hex(text: Optional[str]) -> str:
    if not text:
        return ""
    text = clean_value(text) or ""
    tokens = re.findall(r"(portal[a-f0-9])", text, flags=re.IGNORECASE)
    if not tokens:
        tokens = re.findall(r":(portal[a-f0-9]):", text, flags=re.IGNORECASE)
    if tokens:
        return "".join(GLYPH_MAP.get(t.lower(), "?") for t in tokens)
    fallback = re.findall(r"[0-9A-Fa-f]+", text)
    if fallback:
        return "".join(fallback)
    return text.strip()

# -----------------------------
# Template detection
# -----------------------------
def detect_template_type(text: str) -> Optional[str]:
    if not text:
        return None
    normalized = normalize_line(text)
    lower = normalized.lower()
    if "system colour" in lower or "system color" in lower or "system classification" in lower:
        return "system"
    if "planet type" in lower or "planet glyphs" in lower:
        return "planet"
    if "flora type" in lower:
        return "flora"
    if "fauna class" in lower:
        return "fauna"
    if "discovery type" in lower or "associated resources" in lower:
        return "archaeology"
    if "mineral type" in lower or "primary resource yield" in lower:
        return "mineral"
    for line in normalized.splitlines():
        l = line.strip().lower()
        if "system colour" in l or "system classification" in l:
            return "system"
        if "planet type" in l or "planet glyphs" in l:
            return "planet"
        if "flora type" in l:
            return "flora"
        if "fauna class" in l:
            return "fauna"
        if "discovery type" in l:
            return "archaeology"
        if "mineral type" in l:
            return "mineral"
    return None

# -----------------------------
# Meta builder
# -----------------------------
def build_meta(message: discord.Message) -> dict:
    return {
        "thread_id": message.channel.id,
        "message_id": message.id,
        "submitted_by": message.author.id,
        "timestamp": message.created_at.isoformat()
    }

# -----------------------------
# Generic helpers for description blocks
# -----------------------------
def collect_multiline_field(lines: List[str], start_index: int) -> (str, int):
    collected = []
    i = start_index
    while i < len(lines):
        raw = lines[i]
        clean = normalize_line(raw)
        if clean.startswith("--") or (":" in clean and re.match(r"^[A-Za-z0-9 \-]+:", clean)):
            break
        collected.append(raw.strip())
        i += 1
    return ("\n".join(collected).strip(), i - 1)

# -----------------------------
# Shared heuristics
# -----------------------------
def looks_like_glyphs(s: Optional[str]) -> bool:
    if not s:
        return False
    if re.search(r":portal[a-f0-9]:", s, flags=re.IGNORECASE):
        return True
    if re.search(r"portal[a-f0-9]", s, flags=re.IGNORECASE):
        return True
    if re.search(r"[0-9A-Fa-f]{6,}", s):
        return True
    return False

def find_lookahead_block(lines: List[str], start: int, max_lines: int = 6) -> str:
    collected = []
    j = start
    while j < len(lines) and j < start + max_lines:
        nxt = normalize_line(lines[j])
        if not nxt:
            j += 1
            continue
        if ":" in nxt and re.match(r"^[A-Za-z0-9 \-]+:", nxt):
            break
        collected.append(nxt)
        j += 1
    return " ".join(collected).strip()

# -----------------------------
# System parser (Option C, integrated)
# -----------------------------
def parse_system_entry(message: discord.Message) -> dict:
    raw_lines = [l for l in (message.content or "").splitlines()]
    system = {
        "name": None,
        "classification": None,
        "region": None,
        "special_note": None,
        "code_raw": None,
        "code_hex": None,
        "colour": None,
        "lifeform": None,
        "economy": {},
        "conflict": {"status": None, "level": None},
        "planets": None,
        "moons": None,
        "coordinates": None,
        "screenshot_url": None
    }

    i = 0
    while i < len(raw_lines):
        raw = raw_lines[i]
        clean = normalize_line(raw)
        value = clean_value(extract_after_colon(clean))

        if line_contains_field(clean, "System Name"):
            system["name"] = value

        elif line_contains_field(clean, "Region"):
            if value and (len(value.split()) > 8 or re.search(r"\b(cannot|only|via|portal|warp|drive)\b", value, flags=re.IGNORECASE)):
                system["special_note"] = value
            else:
                system["region"] = value

        elif line_contains_field(clean, "System classification"):
            system["classification"] = value

        elif line_contains_field(clean, "SPECIAL NOTE") or line_contains_field(clean, "Special Note"):
            inline = value
            note, last_idx = collect_multiline_field(raw_lines, i + 1)
            system["special_note"] = "\n".join(filter(None, [inline, note])).strip()
            i = last_idx

        elif line_contains_field(clean, "System Code"):
            if value:
                system["code_raw"] = value
                system["code_hex"] = glyphs_to_hex(value)
            else:
                look = find_lookahead_block(raw_lines, i + 1)
                if looks_like_glyphs(look):
                    system["code_raw"] = look
                    system["code_hex"] = glyphs_to_hex(look)
                    # advance past lookahead lines
                    # find how many lines consumed
                    consumed = 0
                    for k in range(i + 1, min(len(raw_lines), i + 7)):
                        if normalize_line(raw_lines[k]).strip():
                            consumed += 1
                        else:
                            break
                    i += consumed

        elif line_contains_field(clean, "System Colour") or line_contains_field(clean, "System Color"):
            system["colour"] = strip_emojis(value)

        elif line_contains_field(clean, "Dominant Lifeform"):
            system["lifeform"] = strip_emojis(value)

        elif line_contains_field(clean, "Economy"):
            econ = strip_emojis(value or "")
            if "//" in econ:
                t, s = econ.split("//", 1)
                system["economy"]["type"] = clean_value(t)
                system["economy"]["status"] = clean_value(s)
            elif "/" in econ:
                t, s = econ.split("/", 1)
                system["economy"]["type"] = clean_value(t)
                system["economy"]["status"] = clean_value(s)
            elif "-" in econ:
                t, s = econ.split("-", 1)
                system["economy"]["type"] = clean_value(t)
                system["economy"]["status"] = clean_value(s)
            else:
                system["economy"]["type"] = econ or None

        elif line_contains_field(clean, "Conflict"):
            conflict = strip_emojis(value or "")
            m = re.match(r"(\d+)\s*[-–]\s*(.+)", conflict)
            if m:
                system["conflict"]["level"] = int(m.group(1))
                system["conflict"]["status"] = clean_value(m.group(2))
                i += 1
                continue
            m = re.search(r"Level\s*(\d+)", conflict, flags=re.IGNORECASE)
            if m:
                system["conflict"]["level"] = int(m.group(1))
                system["conflict"]["status"] = clean_value(conflict.split("(")[0])
                i += 1
                continue
            m = re.match(r"^(\d+)$", conflict)
            if m:
                system["conflict"]["level"] = int(m.group(1))
            else:
                system["conflict"]["status"] = conflict or None

        elif line_contains_field(clean, "Number of Planets"):
            text = (value or "").lower()
            m = re.match(r"(\d+)\s*\+\s*(\d+)", text)
            if m:
                system["planets"] = int(m.group(1))
                system["moons"] = int(m.group(2))
                i += 1
                continue
            m = re.match(r"(\d+).+?(\d+)", text)
            if m:
                system["planets"] = int(m.group(1))
                system["moons"] = int(m.group(2))
                i += 1
                continue
            m = re.match(r"(\d+)", text)
            if m:
                system["planets"] = int(m.group(1))
                system["moons"] = 0
                i += 1
                continue

        elif line_contains_field(clean, "System Coordinates"):
            system["coordinates"] = value

        elif line_contains_field(clean, "Screenshot") or clean.startswith("-- screenshot") or clean.startswith("--"):
            if message.attachments:
                system["screenshot_url"] = message.attachments[0].url
            else:
                url_match = re.search(r"https?://\S+", raw)
                if url_match:
                    system["screenshot_url"] = url_match.group(0)
                else:
                    j = i + 1
                    while j < min(len(raw_lines), i + 4):
                        nxt = raw_lines[j]
                        m = re.search(r"https?://\S+", nxt)
                        if m:
                            system["screenshot_url"] = m.group(0)
                            break
                        j += 1

        elif ":" in clean:
            key_label = clean.split(":", 1)[0]
            key = normalize_key(key_label)
            val = clean_value(extract_after_colon(clean))
            system[key] = val

        i += 1

    if not system["screenshot_url"] and message.attachments:
        system["screenshot_url"] = message.attachments[0].url

    if not system["code_raw"]:
        joined = " ".join(raw_lines)
        if looks_like_glyphs(joined):
            system["code_raw"] = joined
            system["code_hex"] = glyphs_to_hex(joined)

    return {"entry_type": "system", "system": system, "meta": build_meta(message)}

# -----------------------------
# Planet parser
# -----------------------------
def parse_planet_entry(message: discord.Message) -> dict:
    raw_lines = [l for l in (message.content or "").splitlines()]
    planet = {
        "name": None,
        "type": None,
        "glyphs_raw": None,
        "glyphs_hex": None,
        "resources": [],
        "weather": None,
        "sentinel_level": None,
        "flora": None,
        "fauna": None,
        "special_note": None,
        "screenshot_url": None
    }

    i = 0
    while i < len(raw_lines):
        raw = raw_lines[i]
        clean = normalize_line(raw)
        value = clean_value(extract_after_colon(clean))

        if line_contains_field(clean, "Planet Name") or line_contains_field(clean, "Name"):
            planet["name"] = value

        elif line_contains_field(clean, "Planet Type") or line_contains_field(clean, "Type"):
            planet["type"] = value

        elif line_contains_field(clean, "Planet Glyphs") or line_contains_field(clean, "Glyphs"):
            if value:
                raw_g = value
            else:
                raw_g = find_lookahead_block(raw_lines, i + 1)
            planet["glyphs_raw"] = raw_g or planet["glyphs_raw"]
            planet["glyphs_hex"] = glyphs_to_hex(planet["glyphs_raw"]) if planet["glyphs_raw"] else planet["glyphs_hex"]

        elif line_contains_field(clean, "Resources"):
            res = value
            if not res:
                res = find_lookahead_block(raw_lines, i + 1)
            if res:
                items = re.split(r"[,/\\//\-]+", res)
                planet["resources"] = [clean_value(strip_emojis(x)) for x in items if x.strip()]

        elif line_contains_field(clean, "Weather"):
            planet["weather"] = value

        elif line_contains_field(clean, "Sentinel Level") or line_contains_field(clean, "Sentinal Level"):
            s = value or ""
            m = re.match(r"(\d+)\s*[-–]\s*(.+)", s)
            if m:
                planet["sentinel_level"] = clean_value(m.group(1))
            else:
                m2 = re.search(r"(\d+)", s)
                planet["sentinel_level"] = m2.group(1) if m2 else (s or None)

        elif line_contains_field(clean, "Flora"):
            planet["flora"] = value

        elif line_contains_field(clean, "Fauna"):
            planet["fauna"] = value

        elif line_contains_field(clean, "Special Note") or line_contains_field(clean, "SPECIAL NOTE"):
            inline = value
            note = find_lookahead_block(raw_lines, i + 1)
            planet["special_note"] = "\n".join(filter(None, [inline, note])).strip()

        elif line_contains_field(clean, "Screenshot"):
            if message.attachments:
                planet["screenshot_url"] = message.attachments[0].url
            else:
                url = re.search(r"https?://\S+", raw)
                if url:
                    planet["screenshot_url"] = url.group(0)

        elif ":" in clean:
            key_label = clean.split(":", 1)[0]
            key = normalize_key(key_label)
            val = clean_value(extract_after_colon(clean))
            planet[key] = val

        i += 1

    if not planet["screenshot_url"] and message.attachments:
        planet["screenshot_url"] = message.attachments[0].url

    return {"entry_type": "planet", "planet": planet, "meta": build_meta(message)}

# -----------------------------
# Flora parser
# -----------------------------
def parse_flora_entry(message: discord.Message) -> dict:
    raw_lines = [l for l in (message.content or "").splitlines()]
    flora = {
        "name": None,
        "planet": None,
        "star_system": None,
        "galaxy": None,
        "coordinates": None,
        "biome": None,
        "flora_type": None,
        "rarity": None,
        "discovery_date": None,
        "discovered_by": None,
        "description": None,
        "special_note": None,
        "screenshot_url": None
    }

    i = 0
    while i < len(raw_lines):
        raw = raw_lines[i]
        clean = normalize_line(raw)
        value = clean_value(extract_after_colon(clean))

        if line_contains_field(clean, "Name"):
            flora["name"] = value

        elif line_contains_field(clean, "Planet"):
            flora["planet"] = value

        elif line_contains_field(clean, "Star System"):
            flora["star_system"] = value

        elif line_contains_field(clean, "Galaxy"):
            flora["galaxy"] = value

        elif line_contains_field(clean, "Coordinates"):
            flora["coordinates"] = value

        elif line_contains_field(clean, "Biome"):
            flora["biome"] = value

        elif line_contains_field(clean, "Flora Type"):
            flora["flora_type"] = value

        elif line_contains_field(clean, "Rarity"):
            flora["rarity"] = value

        elif line_contains_field(clean, "Discovery Date"):
            flora["discovery_date"] = value

        elif line_contains_field(clean, "Discovered By"):
            flora["discovered_by"] = value

        elif line_contains_field(clean, "Description") or line_contains_field(clean, "Description / Notes"):
            inline = value
            desc, last_idx = collect_multiline_field(raw_lines, i + 1)
            flora["description"] = "\n".join(filter(None, [inline, desc])).strip()
            i = last_idx

        elif line_contains_field(clean, "Special Note") or line_contains_field(clean, "SPECIAL NOTE"):
            inline = value
            note, last_idx = collect_multiline_field(raw_lines, i + 1)
            flora["special_note"] = "\n".join(filter(None, [inline, note])).strip()
            i = last_idx

        elif line_contains_field(clean, "Screenshot"):
            if message.attachments:
                flora["screenshot_url"] = message.attachments[0].url
            else:
                url = re.search(r"https?://\S+", raw)
                if url:
                    flora["screenshot_url"] = url.group(0)

        elif ":" in clean:
            key_label = clean.split(":", 1)[0]
            key = normalize_key(key_label)
            flora[key] = clean_value(extract_after_colon(clean))

        i += 1

    if not flora["screenshot_url"] and message.attachments:
        flora["screenshot_url"] = message.attachments[0].url

    return {"entry_type": "flora", "flora": flora, "meta": build_meta(message)}

# -----------------------------
# Fauna parser
# -----------------------------
def parse_fauna_entry(message: discord.Message) -> dict:
    raw_lines = [l for l in (message.content or "").splitlines()]
    fauna = {
        "name": None,
        "planet": None,
        "star_system": None,
        "galaxy": None,
        "coordinates": None,
        "biome": None,
        "fauna_class": None,
        "temperament": None,
        "activity_pattern": None,
        "rarity": None,
        "discovery_date": None,
        "discovered_by": None,
        "description": None,
        "special_note": None,
        "screenshot_url": None
    }

    i = 0
    while i < len(raw_lines):
        raw = raw_lines[i]
        clean = normalize_line(raw)
        value = clean_value(extract_after_colon(clean))

        if line_contains_field(clean, "Name"):
            fauna["name"] = value

        elif line_contains_field(clean, "Planet"):
            fauna["planet"] = value

        elif line_contains_field(clean, "Star System"):
            fauna["star_system"] = value

        elif line_contains_field(clean, "Galaxy"):
            fauna["galaxy"] = value

        elif line_contains_field(clean, "Coordinates"):
            fauna["coordinates"] = value

        elif line_contains_field(clean, "Biome"):
            fauna["biome"] = value

        elif line_contains_field(clean, "Fauna Class"):
            fauna["fauna_class"] = value

        elif line_contains_field(clean, "Temperament"):
            fauna["temperament"] = value

        elif line_contains_field(clean, "Activity Pattern"):
            fauna["activity_pattern"] = value

        elif line_contains_field(clean, "Rarity"):
            fauna["rarity"] = value

        elif line_contains_field(clean, "Discovery Date"):
            fauna["discovery_date"] = value

        elif line_contains_field(clean, "Discovered By"):
            fauna["discovered_by"] = value

        elif line_contains_field(clean, "Description") or line_contains_field(clean, "Description / Notes"):
            inline = value
            desc, last_idx = collect_multiline_field(raw_lines, i + 1)
            fauna["description"] = "\n".join(filter(None, [inline, desc])).strip()
            i = last_idx

        elif line_contains_field(clean, "Special Note") or line_contains_field(clean, "SPECIAL NOTE"):
            inline = value
            note, last_idx = collect_multiline_field(raw_lines, i + 1)
            fauna["special_note"] = "\n".join(filter(None, [inline, note])).strip()
            i = last_idx

        elif line_contains_field(clean, "Screenshot"):
            if message.attachments:
                fauna["screenshot_url"] = message.attachments[0].url
            else:
                url = re.search(r"https?://\S+", raw)
                if url:
                    fauna["screenshot_url"] = url.group(0)

        elif ":" in clean:
            key_label = clean.split(":", 1)[0]
            key = normalize_key(key_label)
            fauna[key] = clean_value(extract_after_colon(clean))

        i += 1

    if not fauna["screenshot_url"] and message.attachments:
        fauna["screenshot_url"] = message.attachments[0].url

    return {"entry_type": "fauna", "fauna": fauna, "meta": build_meta(message)}

# -----------------------------
# Archaeology parser
# -----------------------------
def parse_archaeology_entry(message: discord.Message) -> dict:
    raw_lines = [l for l in (message.content or "").splitlines()]
    arch = {
        "name": None,
        "discovery_type": None,
        "planet": None,
        "star_system": None,
        "galaxy": None,
        "coordinates": None,
        "biome": None,
        "depth_or_location": None,
        "estimated_age": None,
        "rarity": None,
        "discovery_date": None,
        "discovered_by": None,
        "associated_resources": [],
        "description": None,
        "special_note": None,
        "screenshot_url": None
    }

    i = 0
    while i < len(raw_lines):
        raw = raw_lines[i]
        clean = normalize_line(raw)
        value = clean_value(extract_after_colon(clean))

        if line_contains_field(clean, "Name"):
            arch["name"] = value

        elif line_contains_field(clean, "Discovery Type"):
            arch["discovery_type"] = value

        elif line_contains_field(clean, "Planet"):
            arch["planet"] = value

        elif line_contains_field(clean, "Star System"):
            arch["star_system"] = value

        elif line_contains_field(clean, "Galaxy"):
            arch["galaxy"] = value

        elif line_contains_field(clean, "Coordinates"):
            arch["coordinates"] = value

        elif line_contains_field(clean, "Biome"):
            arch["biome"] = value

        elif line_contains_field(clean, "Depth") or line_contains_field(clean, "Depth or Location"):
            arch["depth_or_location"] = value

        elif line_contains_field(clean, "Estimated Age") or line_contains_field(clean, "Estimated Age / Classification"):
            arch["estimated_age"] = value

        elif line_contains_field(clean, "Rarity"):
            arch["rarity"] = value

        elif line_contains_field(clean, "Discovery Date"):
            arch["discovery_date"] = value

        elif line_contains_field(clean, "Discovered By"):
            arch["discovered_by"] = value

        elif line_contains_field(clean, "Associated Resources"):
            assoc = value
            if not assoc:
                assoc = find_lookahead_block(raw_lines, i + 1)
            if assoc:
                items = re.split(r"[,/\\//\-]+", assoc)
                arch["associated_resources"] = [clean_value(strip_emojis(x)) for x in items if x.strip()]

        elif line_contains_field(clean, "Description") or line_contains_field(clean, "Description / Notes"):
            inline = value
            desc, last_idx = collect_multiline_field(raw_lines, i + 1)
            arch["description"] = "\n".join(filter(None, [inline, desc])).strip()
            i = last_idx

        elif line_contains_field(clean, "Special Note") or line_contains_field(clean, "SPECIAL NOTE"):
            inline = value
            note, last_idx = collect_multiline_field(raw_lines, i + 1)
            arch["special_note"] = "\n".join(filter(None, [inline, note])).strip()
            i = last_idx

        elif line_contains_field(clean, "Screenshot"):
            if message.attachments:
                arch["screenshot_url"] = message.attachments[0].url
            else:
                url = re.search(r"https?://\S+", raw)
                if url:
                    arch["screenshot_url"] = url.group(0)

        elif ":" in clean:
            key_label = clean.split(":", 1)[0]
            key = normalize_key(key_label)
            val = clean_value(extract_after_colon(clean))
            if re.search(r",|/|//|-", val or ""):
                items = re.split(r"[,/\\//\-]+", val)
                arch[key] = [clean_value(strip_emojis(x)) for x in items if x.strip()]
            else:
                arch[key] = val

        i += 1

    if not arch["screenshot_url"] and message.attachments:
        arch["screenshot_url"] = message.attachments[0].url

    return {"entry_type": "archaeology", "archaeology": arch, "meta": build_meta(message)}

# -----------------------------
# Mineral parser
# -----------------------------
def parse_mineral_entry(message: discord.Message) -> dict:
    raw_lines = [l for l in (message.content or "").splitlines()]
    mineral = {
        "name": None,
        "mineral_type": None,
        "planet": None,
        "star_system": None,
        "galaxy": None,
        "coordinates": None,
        "biome": None,
        "formation_type": None,
        "primary_yield": [],
        "secondary_yield": [],
        "rarity": None,
        "discovery_date": None,
        "discovered_by": None,
        "description": None,
        "special_note": None,
        "screenshot_url": None
    }

    i = 0
    while i < len(raw_lines):
        raw = raw_lines[i]
        clean = normalize_line(raw)
        value = clean_value(extract_after_colon(clean))

        if line_contains_field(clean, "Name"):
            mineral["name"] = value

        elif line_contains_field(clean, "Mineral Type"):
            mineral["mineral_type"] = value

        elif line_contains_field(clean, "Planet"):
            mineral["planet"] = value

        elif line_contains_field(clean, "Star System"):
            mineral["star_system"] = value

        elif line_contains_field(clean, "Galaxy"):
            mineral["galaxy"] = value

        elif line_contains_field(clean, "Coordinates"):
            mineral["coordinates"] = value

        elif line_contains_field(clean, "Biome"):
            mineral["biome"] = value

        elif line_contains_field(clean, "Formation Type"):
            mineral["formation_type"] = value

        elif line_contains_field(clean, "Primary Resource Yield"):
            p = value
            if not p:
                p = find_lookahead_block(raw_lines, i + 1)
            if p:
                items = re.split(r"[,/\\//\-]+", p)
                mineral["primary_yield"] = [clean_value(strip_emojis(x)) for x in items if x.strip()]

        elif line_contains_field(clean, "Secondary Resource Yield"):
            s = value
            if not s:
                s = find_lookahead_block(raw_lines, i + 1)
            if s:
                items = re.split(r"[,/\\//\-]+", s)
                mineral["secondary_yield"] = [clean_value(strip_emojis(x)) for x in items if x.strip()]

        elif line_contains_field(clean, "Rarity"):
            mineral["rarity"] = value

        elif line_contains_field(clean, "Discovery Date"):
            mineral["discovery_date"] = value

        elif line_contains_field(clean, "Discovered By"):
            mineral["discovered_by"] = value

        elif line_contains_field(clean, "Description") or line_contains_field(clean, "Description / Notes"):
            inline = value
            desc, last_idx = collect_multiline_field(raw_lines, i + 1)
            mineral["description"] = "\n".join(filter(None, [inline, desc])).strip()
            i = last_idx

        elif line_contains_field(clean, "Special Note") or line_contains_field(clean, "SPECIAL NOTE"):
            inline = value
            note, last_idx = collect_multiline_field(raw_lines, i + 1)
            mineral["special_note"] = "\n".join(filter(None, [inline, note])).strip()
            i = last_idx

        elif line_contains_field(clean, "Screenshot"):
            if message.attachments:
                mineral["screenshot_url"] = message.attachments[0].url
            else:
                url = re.search(r"https?://\S+", raw)
                if url:
                    mineral["screenshot_url"] = url.group(0)

        elif ":" in clean:
            key_label = clean.split(":", 1)[0]
            key = normalize_key(key_label)
            val = clean_value(extract_after_colon(clean))
            if re.search(r",|/|//|-", val or ""):
                items = re.split(r"[,/\\//\-]+", val)
                mineral[key] = [clean_value(strip_emojis(x)) for x in items if x.strip()]
            else:
                mineral[key] = val

        i += 1

    if not mineral["screenshot_url"] and message.attachments:
        mineral["screenshot_url"] = message.attachments[0].url

    return {"entry_type": "mineral", "mineral": mineral, "meta": build_meta(message)}