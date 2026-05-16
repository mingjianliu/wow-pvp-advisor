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

# Maps normalized spec slug → (WoW class name, WoW spec name) as returned by Blizzard API
_SPEC_CLASS_MAP: dict[str, tuple[str, str]] = {
    "restoration-shaman": ("Shaman", "Restoration"),
    "elemental-shaman": ("Shaman", "Elemental"),
    "enhancement-shaman": ("Shaman", "Enhancement"),
    "restoration-druid": ("Druid", "Restoration"),
    "balance-druid": ("Druid", "Balance"),
    "feral-druid": ("Druid", "Feral"),
    "guardian-druid": ("Druid", "Guardian"),
    "holy-paladin": ("Paladin", "Holy"),
    "retribution-paladin": ("Paladin", "Retribution"),
    "protection-paladin": ("Paladin", "Protection"),
    "discipline-priest": ("Priest", "Discipline"),
    "holy-priest": ("Priest", "Holy"),
    "shadow-priest": ("Priest", "Shadow"),
    "mistweaver-monk": ("Monk", "Mistweaver"),
    "windwalker-monk": ("Monk", "Windwalker"),
    "brewmaster-monk": ("Monk", "Brewmaster"),
    "arms-warrior": ("Warrior", "Arms"),
    "fury-warrior": ("Warrior", "Fury"),
    "protection-warrior": ("Warrior", "Protection"),
    "beast-mastery-hunter": ("Hunter", "Beast Mastery"),
    "marksmanship-hunter": ("Hunter", "Marksmanship"),
    "survival-hunter": ("Hunter", "Survival"),
    "affliction-warlock": ("Warlock", "Affliction"),
    "demonology-warlock": ("Warlock", "Demonology"),
    "destruction-warlock": ("Warlock", "Destruction"),
    "unholy-death-knight": ("Death Knight", "Unholy"),
    "frost-death-knight": ("Death Knight", "Frost"),
    "blood-death-knight": ("Death Knight", "Blood"),
    "havoc-demon-hunter": ("Demon Hunter", "Havoc"),
    "vengeance-demon-hunter": ("Demon Hunter", "Vengeance"),
    "arcane-mage": ("Mage", "Arcane"),
    "fire-mage": ("Mage", "Fire"),
    "frost-mage": ("Mage", "Frost"),
    "subtlety-rogue": ("Rogue", "Subtlety"),
    "assassination-rogue": ("Rogue", "Assassination"),
    "outlaw-rogue": ("Rogue", "Outlaw"),
    "augmentation-evoker": ("Evoker", "Augmentation"),
    "devastation-evoker": ("Evoker", "Devastation"),
    "preservation-evoker": ("Evoker", "Preservation"),
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
    return _SPEC_CLASS_MAP.get(spec)
