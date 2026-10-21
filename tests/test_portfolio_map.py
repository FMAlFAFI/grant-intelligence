from classification.portfolio_map import NOT_GIVEN, canonical, count_table, load_name_map

import pandas as pd

NAMES = load_name_map()


def test_arabic_and_english_names_join_the_same_unit():
    unknown = set()
    assert canonical("كلية العدالة الجنائية", NAMES, unknown) == "College of Criminal Justice"
    assert canonical("College of Criminal Justice", NAMES, unknown) == "College of Criminal Justice"
    assert canonical("قسم علم السموم", NAMES, unknown) == "Department of Toxicology"
    assert unknown == set()


def test_empty_and_unknown_values_are_reported():
    unknown = set()
    assert canonical("", NAMES, unknown) == NOT_GIVEN
    assert canonical("College of Space Studies", NAMES, unknown) == "College of Space Studies"
    assert unknown == {"College of Space Studies"}


def test_count_table_keeps_denominators():
    frame = pd.DataFrame({
        "grant_id": ["a", "b", "c", "d"],
        "type": ["small", "small", "large", NOT_GIVEN],
        "funded": [1, 0, 1, 0],
        "budget": [100, 200, 600, 50],
    })
    table = count_table(frame, "type").set_index("value")
    assert table.loc["small", "proposals"] == 2
    assert table.loc["small", "funded"] == 1
    assert table.loc["small", "share_of_proposals"] == 0.5
    assert table["proposals"].sum() == 4
