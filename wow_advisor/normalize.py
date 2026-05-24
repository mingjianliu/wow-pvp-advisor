_SPEC_ALIASES: dict[str, str] = {
    "rsham": "restoration-shaman",
    "resto shaman": "restoration-shaman",
    "resto-shaman": "restoration-shaman",
    "rdruid": "restoration-druid",
    "resto druid": "restoration-druid",
    "hpal": "holy-paladin",
    "holy pal": "holy-paladin",
    "disc": "discipline-priest",
    "disc priest": "discipline-priest",
    "hpriest": "holy-priest",
    "mw": "mistweaver-monk",
    "mistweaver": "mistweaver-monk",
    "arms": "arms-warrior",
    "fury": "fury-warrior",
    "ret": "retribution-paladin",
    "rets": "retribution-paladin",
    "bm": "beast-mastery-hunter",
    "mm": "marksmanship-hunter",
    "surv": "survival-hunter",
    "sv": "survival-hunter",
    "aff": "affliction-warlock",
    "demo": "demonology-warlock",
    "destro": "destruction-warlock",
    "feral": "feral-druid",
    "balance": "balance-druid",
    "boom": "balance-druid",
    "boomkin": "balance-druid",
    "uh": "unholy-death-knight",
    "unholy": "unholy-death-knight",
    "unholy dk": "unholy-death-knight",
    "frost dk": "frost-death-knight",
    "frost": "frost-death-knight",
    "blood": "blood-death-knight",
    "blood dk": "blood-death-knight",
    "havoc": "havoc-demon-hunter",
    "veng": "vengeance-demon-hunter",
    "ele": "elemental-shaman",
    "enhance": "enhancement-shaman",
    "enh": "enhancement-shaman",
    "arcane": "arcane-mage",
    "fire": "fire-mage",
    "frost mage": "frost-mage",
    "sub": "subtlety-rogue",
    "sin": "assassination-rogue",
    "outlaw": "outlaw-rogue",
    "sp": "shadow-priest",
    "shadow": "shadow-priest",
    "aug": "augmentation-evoker",
    "dev": "devastation-evoker",
    "pres": "preservation-evoker",
    "ww": "windwalker-monk",
    "brew": "brewmaster-monk",
    "guardian": "guardian-druid",
    "prot warrior": "protection-warrior",
    "prot pally": "protection-paladin",
    "prot paladin": "protection-paladin",
}

_BRACKET_ALIASES: dict[str, str] = {
    "3v3": "3v3",
    "3vs3": "3v3",
    "2v2": "2v2",
    "2vs2": "2v2",
    "solo": "shuffle",
    "solo shuffle": "shuffle",
    "solo-shuffle": "shuffle",
    "shuffle": "shuffle",
    "rbg": "rbg",
    "blitz": "battlegrounds/blitz",
}

# Maps normalized spec slug -> (Class ID, Spec ID, WoW class name, WoW spec name)
_SPEC_INFO_MAP: dict[str, tuple[int, int, str, str]] = {
    "restoration-shaman": (7, 264, "Shaman", "Restoration"),
    "elemental-shaman": (7, 262, "Shaman", "Elemental"),
    "enhancement-shaman": (7, 263, "Shaman", "Enhancement"),
    "restoration-druid": (11, 105, "Druid", "Restoration"),
    "balance-druid": (11, 102, "Druid", "Balance"),
    "feral-druid": (11, 103, "Druid", "Feral"),
    "guardian-druid": (11, 104, "Druid", "Guardian"),
    "holy-paladin": (2, 65, "Paladin", "Holy"),
    "retribution-paladin": (2, 70, "Paladin", "Retribution"),
    "protection-paladin": (2, 66, "Paladin", "Protection"),
    "discipline-priest": (5, 256, "Priest", "Discipline"),
    "holy-priest": (5, 257, "Priest", "Holy"),
    "shadow-priest": (5, 258, "Priest", "Shadow"),
    "mistweaver-monk": (10, 270, "Monk", "Mistweaver"),
    "windwalker-monk": (10, 269, "Monk", "Windwalker"),
    "brewmaster-monk": (10, 268, "Monk", "Brewmaster"),
    "arms-warrior": (1, 71, "Warrior", "Arms"),
    "fury-warrior": (1, 72, "Warrior", "Fury"),
    "protection-warrior": (1, 73, "Warrior", "Protection"),
    "beast-mastery-hunter": (3, 253, "Hunter", "Beast Mastery"),
    "marksmanship-hunter": (3, 254, "Hunter", "Marksmanship"),
    "survival-hunter": (3, 255, "Hunter", "Survival"),
    "affliction-warlock": (9, 265, "Warlock", "Affliction"),
    "demonology-warlock": (9, 266, "Warlock", "Demonology"),
    "destruction-warlock": (9, 267, "Warlock", "Destruction"),
    "unholy-death-knight": (6, 252, "Death Knight", "Unholy"),
    "frost-death-knight": (6, 251, "Death Knight", "Frost"),
    "blood-death-knight": (6, 250, "Death Knight", "Blood"),
    "havoc-demon-hunter": (12, 577, "Demon Hunter", "Havoc"),
    "vengeance-demon-hunter": (12, 581, "Demon Hunter", "Vengeance"),
    "arcane-mage": (8, 62, "Mage", "Arcane"),
    "fire-mage": (8, 63, "Mage", "Fire"),
    "frost-mage": (8, 64, "Mage", "Frost"),
    "subtlety-rogue": (4, 261, "Rogue", "Subtlety"),
    "assassination-rogue": (4, 259, "Rogue", "Assassination"),
    "outlaw-rogue": (4, 260, "Rogue", "Outlaw"),
    "augmentation-evoker": (13, 1473, "Evoker", "Augmentation"),
    "devastation-evoker": (13, 1467, "Evoker", "Devastation"),
    "preservation-evoker": (13, 1468, "Evoker", "Preservation"),
}


def normalize_spec(raw: str) -> str:
    key = raw.strip().lower()
    if key in _SPEC_ALIASES:
        return _SPEC_ALIASES[key]
    return key.replace(" ", "-")


def normalize_bracket(raw: str) -> str:
    key = raw.strip().lower()
    return _BRACKET_ALIASES.get(key, key)


def spec_to_class_spec(spec: str) -> tuple[str, str] | None:
    """Return (class_name, spec_name) as Blizzard API returns them, or None if unknown."""
    info = _SPEC_INFO_MAP.get(spec)
    if info:
        return info[2], info[3]
    return None


def spec_to_ids(spec: str) -> tuple[int, int] | None:
    """Return (class_id, spec_id), or None if unknown."""
    info = _SPEC_INFO_MAP.get(spec)
    if info:
        return info[0], info[1]
    return None
