from wow_advisor.talent_tree import _parse_node

def test_parse_choice_node_extracts_spell_id():
    node_data = {
        "id": 12345,
        "node_type": {"id": 2, "type": "choice"},
        "ranks": [
            {
                "choice_of_tooltips": [
                    {
                        "talent": {"name": "Choice A"},
                        "spell_tooltip": {"spell": {"id": 67890}}
                    }
                ]
            }
        ],
        "display_col": 1,
        "display_row": 1,
        "unlocks": []
    }
    parsed = _parse_node(node_data)
    assert parsed is not None
    assert parsed["spellId"] == 67890
    assert parsed["type"] == "diamond"
