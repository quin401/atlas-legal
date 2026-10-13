"""Safety guard: refuse to run next to common online anti-cheat services.

This tool is for offline / single-player / bot-match use. Online anti-cheat
systems exist to keep real-player matches fair, and using any aim assist next
to them is both unfair to other players and a fast way to get banned.
"""

from __future__ import annotations

import psutil

# Lower-case process names (without .exe) of common anti-cheat components.
ANTICHEAT_PROCESSES = frozenset({
    "easyanticheat", "easyanticheat_eos", "easyanticheat_launcher",
    "beservice", "beclient", "battleye", "bedaisy",
    "vgc", "vgtray",                 # Riot Vanguard
    "faceit", "faceitclient",
    "eac_launcher",
    "equ8", "xigncode", "x3", "gameguard", "npggnt", "ahnlab",
    "punkbuster", "pnkbstra", "pnkbstrb",
    "ricochet",                      # Call of Duty
})


def _norm(name: str) -> str:
    name = name.lower()
    return name[:-4] if name.endswith(".exe") else name


def find_anticheat(running: list[str], extra: list[str] | None = None) -> list[str]:
    """Return the anti-cheat process names present in ``running``."""
    blocked = ANTICHEAT_PROCESSES | {_norm(n) for n in (extra or [])}
    return sorted({_norm(n) for n in running} & blocked)


def running_process_names() -> list[str]:
    names = []
    for p in psutil.process_iter(["name"]):
        try:
            if p.info["name"]:
                names.append(p.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return names
