"""
One spelling per value for the EMPRI 2018 table columns.

The field teams typed the same thing many ways ("Throny wire", "Thron wire", "Thorn Wire";
"Cf", "Cattle feeding", "Cattal feeding"). Two treatments:

  lists  columns with a small closed vocabulary become a ';' list of canonical lowercase terms,
         using the abbreviations the report itself defines (Vol II legend table). "No"/"Nil" -> "none".
  text   free-text columns keep their wording but get consistent casing, spacing and spelling,
         with the report's own abbreviations spelled out where they are unambiguous.

The caller keeps the original cell in a *Text column.
"""

import re

# ------------------------------------------------------------------ closed vocabularies
# Each entry: canonical term -> regex matched against one lowercased part of the cell.

NONE = r"no|nil|nill|none|not observed|nob|no fence|n0|0"

LISTS = {
    "fenceType": {
        "none": NONE,
        "mesh": r"mesh",
        "wall": r"(partial(ly)?[- ]?)?(stone |cement |compound )?wall",
        "thorn wire": r"(partial(ly)?)?\s*(thorn|throny|thron|thory|thorm|thorny)\s*wire|t",
    },
    "presentStatus": {
        "clean": r"clean( water)?|clear|unpolluted",
        "muddy": r"(slight(ly)?\s*)?muddy( water)?|puddle\s*muddy water",
        "polluted": r"(slightly |lightly )?pollut(ed|\.)?( water| puddle)?",
        "sewage": r"sewage|was?t\s*e?water drain",
        "stp water": r"stp water",
        "dry": r"dry|dried",
        "green water": r"green(ish)?( ?colou?r)?( water)?",
        "puddle": r"puddle",
        "marshy": r"marshy",
        "none": r"no",
    },
    "waterUsage": {
        "none": NONE,
        "cattle feeding": r"c\.?f\.?|cattle ?feeding(/ ?grazing)?|cattal feeding|(cattle ?)?grazing",
        "irrigation": r"i|irr[iea]gat(ion)?",
        "fishing": r"f|fishing|fisher(y|ies)",
        "washing": r"w|wash(ing)?|cloth washing",
        "bathing": r"bathing",
        "boating": r"boating",
        "park maintenance": r"park( ?maint(enance|anance)?)?",
        "religious activity": r"r\.? ?act\.?|relig(ious|\.) ?activity",
        "recreation": r"rc|recreation(al)?",
        "groundwater recharge": r"ground ?water ?rechar(ge)?",
        "groundwater extraction": r"ground ?water ?extract(ion)?",
        "flood mitigation": r"flood ?mitigation",
        "construction": r"const(ruction|r)?\.? ?activity",
        "aesthetic": r"aesthetic use",
    },
    "vegetationCover": {"none": NONE, "partial": r"partial(ly)?|partly", "complete": r"complete(ly)?", "dry": r"dry"},
    "weeds": {"none": NONE, "partial": r"partial(ly)?|partly|partillay", "complete": r"complete(ly)?", "yes": r"yes"},
    "vegetationType": {
        "none": NONE,
        "growing on bank": r"(growi?ng|gr\.) on bank",
        "emergent": r"emergent",
        "free floating": r"free floating",
        "terrestrial": r"terrestrial( plants)?",
        "aquatic plants": r"aquatic plants?",
        "weeds": r"weeds",
        "dry": r"dry",
        "partial": r"partial",
    },
    "aquaticFlora": {
        "none": NONE,
        "emergent": r"e|em|emerg(ent|\.)?( \(ipomea\))?",
        "submerged": r"s|subm(erged|erg)?",
        "rooted floating": r"(r|rt)\. ?(flo(ating|at)?\.?|fl\.?)|r\.floating",
        "free floating": r"(f|fr)\.? ?(flo(ating|at)?\.?|fl\.?)|free ?(flo(ating|at)?\.?)",
        "floating": r"fl\.?|floating",
        "weeds": r"weeds",
        "dry": r"dry",
    },
    "fauna": {
        "none": NONE,
        "birds": r"b|birds?",
        "butterflies": r"b\.? ?fl(y|ies)|bt\.?|bf\.?|bt\.? ?fly|bt\.? ?fl(ies|ys)|butterfl(y|ies)|bt fly",
        "dragonflies": r"d\.? ?fly|dr\.? ?fl(y|ys|ies)\.?|drg ?fly|d \.fly",
        "fish": r"f|fish",
        "frogs": r"frogs?|a|amphibians?",
        "molluscs": r"m|molluscs?",
        "reptiles": r"r|reptiles?",
        "livestock": r"livestock",
        "snakes": r"snakes?",
        "snails": r"snails?",
        "tortoises": r"torto?ises?",
        "lizards": r"lizards?",
    },
    "visitingAnimals": {
        "none": NONE,
        "cattle": r"cattles?|c",
        "cow": r"cows?",
        "goat": r"g|goats?",
        "sheep": r"s|sheep",
        "buffalo": r"b|buffalo(es)?",
        "pig": r"pigs?",
        "dog": r"dogs?",
        "cat": r"cats?",
        "rat": r"rats?",
        "squirrel": r"squirrels?",
        "rabbit": r"rabbits?",
        "mongoose": r"man?goose|mongoose",
        "birds": r"birds",
        "reptiles": r"reptiles",
        "wild animals": r"wild animals",
    },
}

OWNERS = {
    "none": NONE,
    "unknown": r"unknown",
    "private": r"priv(ate|\.)?|pvt\.?|private developers?|pvt\.? develop\.?",
    "public": r"publ?(ic|\.)?|local (people|residents)",
    "government": r"govt\.?|government|govt",
    "farmers": r"farm(er|ers|ar)?",
    "developers": r"(layout )?dev(e)?lopers?",
    "BBMP": r"bbmp", "BDA": r"bda", "NICE": r"nice", "KHB": r"khb", "BEL": r"bel", "KSPCB": r"kspcb",
    "army": r"army|military area", "air force": r"air ?force", "forest department": r"forest dept\.?",
}
LISTS["convertedBy"] = OWNERS
LISTS["encroachedBy"] = OWNERS

# Agencies and the spellings used for them in the custodian column.
CUSTODIANS = {
    "BBMP": r"bbmp", "BDA": r"bda", "ZP": r"zp", "KFD": r"kfd|forest", "MI": r"mi|minor irrigation",
    "KLCDA": r"klcda", "CRPF": r"crpf", "Army": r"army area|army", "Air Force": r"inside air force|air force",
    "ISRO": r"isro", "Horticulture Department": r"horti\. dept", "MPA": r"mpa",
}

COMPASS = {"north": "N", "south": "S", "east": "E", "west": "W", "northeast": "NE", "northwest": "NW",
           "southeast": "SE", "southwest": "SW"}


def split_parts(text):
    """'I, F, B, W & Cf' -> ['I', 'F', 'B', 'W', 'Cf']. Splits on , / ; 'and' and on & unless it joins a name ('AS&ET')."""
    t = re.sub(r"(?<![A-Z])&|&(?![A-Z])|\band\b", ",", text)
    return [p.strip(" .") for p in re.split(r"[,/;]", t) if p.strip(" .")]


def to_list(column, text):
    """Returns (terms, unknown_parts). Parts outside the vocabulary are kept as written."""
    table = LISTS[column]
    terms, unknown = [], []
    for part in split_parts(text):
        part = re.sub(r"\s+", " ", part).strip(" .,")
        key = part.lower()
        hit = next((term for term, rx in table.items() if re.fullmatch(rx, key)), None)
        if hit is None:
            unknown.append(part)
            hit = part
        if hit not in terms:
            terms.append(hit)
    if len(terms) > 1 and "none" in terms:
        terms.remove("none")
    return terms, unknown


def custodian(text):
    out = []
    for part in re.split(r"\s*/\s*", text):
        hit = next((k for k, rx in CUSTODIANS.items() if re.fullmatch(rx, part.strip().lower())), None)
        out.append(hit or part.strip())
    return out


def directions(text):
    """'N, NE & South East' -> ['N', 'NE', 'SE']; phrases like 'Center of lake' are kept."""
    out = []
    t = text.replace("&", ",").replace(" and ", ",")
    for part in re.split(r"[,;]", t):
        key = re.sub(r"[^a-z]", "", part.lower())
        if not key:
            continue
        code = COMPASS.get(key) or (key.upper() if re.fullmatch(r"(n|s|e|w|ne|nw|se|sw)", key) else None)
        if code is None and re.fullmatch(r"(north|south|east|west)(north|south|east|west)?", key):
            code = "".join(COMPASS[w][0] for w in re.findall(r"north|south|east|west", key))
        if code is None:
            if key in ("no", "nil", "none"):
                code = "none"
            elif key in ("alldirection", "alldirections"):
                code = "all"
            else:
                code = re.sub(r"\s+", " ", part.strip(" .")).lower()
        if code not in out:
            out.append(code)
    return out


# ------------------------------------------------------------------ free text

# Abbreviations from the report's legend (Vol II, "Short form" table) and frequent typing variants.
TEXT_FIXES = [
    (r"\bagri\.?(?=[\s,&]|$)", "agriculture"), (r"\bagricultural\b", "agriculture"), (r"\bag\.? land\b", "agriculture land"),
    (r"\bagri\.? land\b", "agriculture land"), (r"\bvl\.?(?=[\s,&]|$)", "vacant land"), (r"\bv\. ?land\b", "vacant land"),
    (r"\bpl\.(?=[\s,&]|$)", "plantation"), (r"\bplant\.(?=[\s,&]|$)", "plantation"), (r"\beucalptus\b", "eucalyptus"),
    (r"\bbuild\.(?=[\s,&]|$)", "buildings"), (r"\bbuliding\b", "building"), (r"\bgovt\.?(?=[\s,&]|$)", "government"),
    (r"\bpvt\.?(?=[\s,&]|$)", "private"), (r"\bpriv\.(?=[\s,&]|$)", "private"), (r"\bpubl\.(?=[\s,&]|$)", "public"),
    (r"\brd\.(?=[\s,&]|$)", "road"), (r"\bgrave ?yard\b", "graveyard"), (r"\bdepo\b", "depot"),
    (r"\bresarch\b", "research"), (r"\bsettlment\b", "settlement"), (r"\bchruch\b", "church"),
    (r"\bthe ?(?=\w)", "the "), (r"\bh\. ?defecat(ion|\.)?", "human defecation"), (r"\bcd\b", "construction debris"),
    (r"\bgd\b", "garbage dump"), (r"\bsewega\b", "sewage"), (r"\bdumpings\b", "dumping"), (r"\brun ?off", "runoff"),
    (r"\bcattle ?wading\b", "cattle wading"), (r"\bmud ?heaps?\b", "mud heap"), (r"\bbiomed\.", "biomedical"),
]

# surroundingArea uses single-letter codes from the legend.
AREA_CODES = {
    "a": "agriculture", "b": "buildings", "bf": "brick factory", "bl": "barren land", "f": "forest",
    "g": "gomala", "gy": "graveyard", "h": "hotel", "hl": "hillock", "i": "industry", "l": "layout",
    "n": "nursery", "pl": "plantation", "q": "quarry pit", "r": "resort", "s": "settlement", "sc": "school",
    "t": "temple", "vl": "vacant land", "rt": "railway track",
}


# dumpingType codes from the legend.
DUMP_CODES = {
    "a": "ash", "ag": "agriculture waste", "b": "brick waste", "bm": "biomedical waste", "d": "debris",
    "g": "garbage", "gr": "garment waste", "i": "industrial waste", "o": "organic waste", "p": "plastic",
    "pl": "plastic", "pt": "poultry waste", "t": "tyres",
}


def recase(text, proper):
    """Sentence case: words go lowercase unless they are acronyms or proper names; first letter up."""
    def word(m):
        w = m.group(0)
        if len(w) > 1 and (w.isupper() or w.rstrip(".").isupper()):
            return w
        return w if w.rstrip(".") in proper else w.lower()

    out = re.sub(r"[A-Za-z][A-Za-z'.]*", word, text)
    return out[:1].upper() + out[1:]


def expand_codes(text, codes):
    return re.sub(r"(?<![\w.])([A-Za-z]{1,2})\.?(?=\s*(?:,|&|$))", lambda m: codes.get(m.group(1).lower(), m.group(0)), text)


def tidy_text(text, proper, codes=None):
    if re.fullmatch(r"(?i)\s*(no|nil|none)\s*", text):
        return "none"
    t = re.sub(r"(?<=[a-z]{2})\.(?=[A-Za-z]{2})", ". ", text)  # "Agri.runoff"
    t = re.sub(r"\s*&\s*", " & ", t)
    t = re.sub(r"\s*,\s*", ", ", t)
    t = re.sub(r"\s+", " ", t).strip(" ,")
    if codes:
        t = expand_codes(t, codes)
    for rx, rep in TEXT_FIXES:
        t = re.sub(rx, rep, t, flags=re.I)
    return recase(t, proper)


LIST_COLUMNS = list(LISTS)
TEXT_COLUMNS = ["surroundingArea", "convertedTo", "encroachedFor", "dumpingType", "pollutant"]
DIRECTION_COLUMNS = ["encroachmentDirection", "dumpingDirection", "sewageInflow"]


def normalise(row, proper):
    """Adds <column>Text with the original cell and rewrites the column. Returns unknown list terms."""
    unknown = []
    for col in LIST_COLUMNS:
        value = row.get(col)
        row[col + "Text"] = value
        if value:
            terms, miss = to_list(col, value)
            row[col] = terms
            unknown.extend((col, m) for m in miss)
    for col in DIRECTION_COLUMNS:
        value = row.get(col)
        row[col + "Text"] = value
        if value:
            row[col] = directions(value)
    for col in TEXT_COLUMNS:
        value = row.get(col)
        row[col + "Text"] = value
        if value:
            codes = AREA_CODES if col == "surroundingArea" else DUMP_CODES if col == "dumpingType" else None
            row[col] = tidy_text(value, proper, codes)
    value = row.get("custodian")
    row["custodianText"] = value
    if value:
        row["custodian"] = custodian(value)
    return unknown
