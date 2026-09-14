"""Small value parsers shared by the section builders."""

ACRE_M2 = 4046.86


def num(value):
    """A number from a CSV cell, int when whole; None for blanks and junk."""
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return int(f) if f.is_integer() else round(f, 4)


def flag(value):
    return {"true": True, "false": False, "yes": True, "no": False}.get(str(value).strip().lower()) if value not in (None, "") else None


def split_list(value):
    return [v.strip() for v in (value or "").split(";") if v.strip()]


def acres_from_m2(m2):
    m2 = num(m2)
    return None if m2 is None else round(m2 / ACRE_M2, 2)


NONE_WORDS = {"none", "no", "nil", "unknown"}


def words(value):
    """A ';' list from a vocabulary column, without the "none" placeholder."""
    return [w for w in split_list(value) if w.lower() not in NONE_WORDS]


def meaningful(value):
    return None if value is None or value.strip().lower() in NONE_WORDS else value
