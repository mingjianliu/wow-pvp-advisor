from wow_advisor.normalize import normalize_spec, normalize_bracket, spec_to_class_spec


def test_normalize_spec_exact():
    assert normalize_spec("restoration-shaman") == "restoration-shaman"


def test_normalize_spec_spaces():
    assert normalize_spec("restoration shaman") == "restoration-shaman"


def test_normalize_spec_alias_rsham():
    assert normalize_spec("rsham") == "restoration-shaman"


def test_normalize_spec_alias_resto():
    assert normalize_spec("resto shaman") == "restoration-shaman"


def test_normalize_spec_case():
    assert normalize_spec("Restoration Shaman") == "restoration-shaman"


def test_normalize_spec_unknown_passthrough():
    assert normalize_spec("arms warrior") == "arms-warrior"


def test_normalize_bracket_3v3():
    assert normalize_bracket("3v3") == "3v3"
    assert normalize_bracket("3V3") == "3v3"


def test_normalize_bracket_solo():
    assert normalize_bracket("solo") == "solo-shuffle"
    assert normalize_bracket("solo shuffle") == "solo-shuffle"


def test_normalize_bracket_2v2():
    assert normalize_bracket("2v2") == "2v2"


def test_spec_to_class_spec_shaman():
    cls, spec = spec_to_class_spec("restoration-shaman")
    assert cls == "Shaman"
    assert spec == "Restoration"


def test_spec_to_class_spec_rogue():
    cls, spec = spec_to_class_spec("subtlety-rogue")
    assert cls == "Rogue"
    assert spec == "Subtlety"


def test_spec_to_class_spec_unknown_returns_none():
    result = spec_to_class_spec("unknown-spec")
    assert result is None


# --- Devourer Demon Hunter --------------------------------------------------
#
# Blizzard lists 40 playable specs; the spec map had 39. Devourer (spec id 1480)
# was absent, so it could not be queried at all despite holding 5002 entries on
# the Season 1 solo-shuffle leaderboard.

def test_devourer_demon_hunter_is_known():
    from wow_advisor.normalize import spec_to_ids
    assert spec_to_ids("devourer-demon-hunter") == (12, 1480)


def test_devourer_demon_hunter_class_and_spec_names():
    assert spec_to_class_spec("devourer-demon-hunter") == ("Demon Hunter", "Devourer")


def test_devourer_alias():
    assert normalize_spec("devourer") == "devourer-demon-hunter"


def test_spec_map_covers_every_playable_spec():
    """40 specs live in the API; drift here means a spec silently cannot be queried."""
    from wow_advisor.normalize import _SPEC_INFO_MAP
    assert len(_SPEC_INFO_MAP) == 40


# --- Blitz bracket ----------------------------------------------------------
#
# 'battlegrounds/blitz' 404s. The live leaderboards are 'blitz-overall' and
# per-spec 'blitz-{class}-{spec}', mirroring solo shuffle.

def test_blitz_normalizes_to_blitz():
    assert normalize_bracket("blitz") == "blitz"


def test_blitz_aliases():
    assert normalize_bracket("Blitz") == "blitz"
    assert normalize_bracket("solo blitz") == "blitz"
    assert normalize_bracket("bg blitz") == "blitz"
