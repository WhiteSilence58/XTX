"""
Logitech Serial Generator
Format: YY WW WERK LINIE LAUF 8  (immer 12 Zeichen)
"""
import itertools
import string
import datetime

CHARS = string.ascii_uppercase + string.digits  # A-Z0-9, 36 Zeichen

# Bekannte Werk+Linie Prefixes aus echten Serials (nach YYWW)
# Jeder Eintrag: (prefix_nach_yyww, verbleibende_lauf_stellen)
# Gesamtlänge Serial = 12 → verbleibend = 12 - 4(yyww) - len(prefix) - 1(suffix'8')
KNOWN_PREFIXES = [
    # Combo Touch M4 13"
    "LZ91GL", "LZ91GM", "LZ91GN", "LZ91GQ",
    # Combo Touch M4 11"
    "LZ90GQ",
    # Combo Touch iPad Pro 12.9"
    "LZ90F0", "LZ90F",
    # PRO X Superlight 2
    "LZ03NY",
    # PRO X Superlight 1
    "LZ01HT",
    # MX Master 3S Mac
    "LZ50LE", "LZ50LD", "LZ50LF",
    # G923 Lenkrad
    "LZG0XF", "LZG0XE", "LZG0XD", "LZG0XG", "LZG0XH",
    # G923 Xbox 2026
    "LZG0XG",
    # Lenkräder alt
    "LZG0HF", "LZG0HG", "LZG0HH",
    # PRO X TKL Weiss
    "MR330A", "MR330B", "MR330C",
    # PRO X TKL Pink
    "MR2C70", "MR2C71",
    # PRO X TKL Black
    "MR16DE", "MR16DF",
    # G715
    "MR3E82", "MR3E83", "MR3E84", "MR3E85", "MR3E87",
    # G Pro TKL old
    "MR2247",
    # MX Mechanical Mini schwarz
    "SCU01P", "SCU01Q", "SCU01R", "SCU01S", "SCU01T",
    # MX Mechanical Mini weiss
    "SCU05G", "SCU05H", "SCU05J", "SCU05K", "SCU05L", "SCU05M",
    # G Cloud
    "TN0255",
    # Remote Control
    "LZA2JH",
    # G Pro Lenkrad Xbox / Tap / Presenter
    "WD01A4",
    # Rally Bar Mini
    "FDZ3YE",
    # Combo Touch iPad Pro 11"
    "LZN014", "LZN004",
    # Combo Touch 10
    "LZ939W",
    # Slim Folio / Rugged / A20
    "LZ91GQ",
]

# Breite Werke für Phase 2
WERKE = ["LZ", "MR", "SC", "WD", "TN", "FD"]


def weeks_in_year(year: int) -> int:
    last = datetime.date(year, 12, 28)
    return last.isocalendar()[1]


def _serial_len_ok(yyww: str, prefix: str, lauf_len: int) -> bool:
    return len(yyww) + len(prefix) + lauf_len + 1 == 12


def gen_known(year_start: int, year_end: int):
    """Phase 1: bekannte Prefixes × alle YYWW im Bereich."""
    for year in range(2000 + year_start, 2000 + year_end + 1):
        yy = str(year)[-2:]
        for week in range(1, weeks_in_year(year) + 1):
            ww = f"{week:02d}"
            yyww = yy + ww
            for prefix in KNOWN_PREFIXES:
                lauf_len = 12 - 4 - len(prefix) - 1  # -1 für suffix '8'
                if lauf_len < 1:
                    continue
                for combo in itertools.product(CHARS, repeat=lauf_len):
                    yield yyww + prefix + "".join(combo) + "8"


def gen_broad(year_start: int, year_end: int):
    """Phase 2: breiter Scan — alle Werke, alle Linie+Lauf Kombinationen."""
    for year in range(2000 + year_start, 2000 + year_end + 1):
        yy = str(year)[-2:]
        for week in range(1, weeks_in_year(year) + 1):
            ww = f"{week:02d}"
            yyww = yy + ww
            for werk in WERKE:
                # Linie (2 Zeichen) + Lauf (4 Zeichen) + '8' = 8 Zeichen → total 12
                remaining = 12 - 4 - len(werk) - 1  # = 12 - 4 - 2 - 1 = 5
                if remaining < 3:
                    continue
                for combo in itertools.product(CHARS, repeat=remaining):
                    yield yyww + werk + "".join(combo) + "8"


class SerialGenerator:
    def __init__(self, year_start=23, year_end=26):
        self.year_start = year_start
        self.year_end   = year_end

    def all_serials(self):
        seen = set()
        for s in gen_known(self.year_start, self.year_end):
            if s not in seen:
                seen.add(s)
                yield s
        for s in gen_broad(self.year_start, self.year_end):
            if s not in seen:
                seen.add(s)
                yield s


def estimate_total(year_start=23, year_end=26) -> dict:
    years = year_end - year_start + 1
    avg_weeks = 52
    known_est = len(KNOWN_PREFIXES) * years * avg_weeks * (36 ** 2)
    broad_est = len(WERKE) * years * avg_weeks * (36 ** 5)
    return {
        "total_estimate":    known_est + broad_est,
        "known_estimate":    known_est,
        "broad_estimate":    broad_est,
        "known_prefixes":    len(KNOWN_PREFIXES),
        "years":             years,
    }
