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
