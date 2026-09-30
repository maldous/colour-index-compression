import hashlib

from benchmarks import hutter_opportunity_inputs as inputs


def _spec(opportunity: str, strength: str) -> dict:
    return {"opportunity": opportunity, "strength": strength, "target_bytes": 32768,
            "repetition": 4, "variation": 3, "distance": 5, "noise": 2,
            "dictionary_cardinality": 7, "seed": 91}


def test_default_inputs_are_exact_sized_reproducible_and_strengths_share_seed():
    specs = inputs.default_specs(32768)
    assert len(specs) == len(inputs.CLASSES) * len(inputs.STRENGTHS)
    for opportunity in inputs.CLASSES:
        group = [spec for spec in specs if spec["opportunity"] == opportunity]
        assert len({spec["seed"] for spec in group}) == 1
    for spec in specs:
        first = inputs.generate(spec)
        assert len(first) == 32768 and first == inputs.generate(dict(spec))
        assert inputs.provenance(spec)["input_sha256"] == hashlib.sha256(first).hexdigest()


def test_pages_have_realistic_xml_container_and_wikitext_fields():
    for opportunity in inputs.CLASSES:
        data = inputs.generate(_spec(opportunity, "strong"))
        assert data.startswith(b"<mediawiki>\n<page><title>")
        assert b"<revision><id>" in data
        assert b"<contributor><username>" in data
        assert b'<text xml:space="preserve">' in data
        assert b"</text></revision></page>" in data


def test_repeated_body_control_has_measured_family_and_literal_separation():
    strong = inputs.provenance(_spec("repeated_body_families", "strong"))["mechanistic_diagnostics"]
    weak = inputs.provenance(_spec("repeated_body_families", "weak"))["mechanistic_diagnostics"]
    absent = inputs.provenance(_spec("repeated_body_families", "absent"))["mechanistic_diagnostics"]
    assert strong["literal_repeat_occurrences"] > weak["literal_repeat_occurrences"] > 0
    assert absent["literal_repeat_occurrences"] == 0
    absent_data = inputs.generate(_spec("repeated_body_families", "absent"))
    assert b"unique-literal-" in absent_data and b"The census of" not in absent_data


def test_numeric_relation_is_exactly_removed_by_absent_control():
    strong = inputs.provenance(_spec("numeric_conditional", "strong"))["mechanistic_diagnostics"]
    weak = inputs.provenance(_spec("numeric_conditional", "weak"))["mechanistic_diagnostics"]
    absent = inputs.provenance(_spec("numeric_conditional", "absent"))["mechanistic_diagnostics"]
    assert strong["numeric_relation_true_rows"] > weak["numeric_relation_true_rows"] > 0
    assert absent["numeric_relation_true_rows"] == 0


def test_title_redirect_and_topology_relations_are_measured_not_markers():
    cases = (("title_link_reuse", "title_link_relation"),
             ("redirect_metadata", "redirect_metadata_relation"),
             ("category_url_topology", "category_url_relation"),
             ("infobox_table_relations", "table_relation"))
    for opportunity, relation in cases:
        strong = inputs.provenance(_spec(opportunity, "strong"))["mechanistic_diagnostics"]
        absent = inputs.provenance(_spec(opportunity, "absent"))["mechanistic_diagnostics"]
        weak = inputs.provenance(_spec(opportunity, "weak"))["mechanistic_diagnostics"]
        assert strong[relation + "_true_rows"] > weak[relation + "_true_rows"] > 0
        assert absent[relation + "_true_rows"] == 0


def test_parameter_perturbation_changes_shared_generator_input():
    spec = _spec("field_dictionary_composition", "weak")
    assert inputs.generate(spec) != inputs.generate({**spec, "seed": spec["seed"] + 1, "noise": 9})


def test_one_factor_sweep_is_paired_and_changes_one_baseline_dimension():
    sweep = inputs.one_factor_sweep_specs()
    assert len(sweep) == len(inputs.CLASSES) * 20
    keys = {"repetition", "distance", "dictionary_cardinality", "frequency", "variation",
            "variation_type", "noise", "exception_rate_permille", "prose_mixture_permille", "target_bytes"}
    for opportunity in inputs.CLASSES:
        rows = [row for row in sweep if row["opportunity"] == opportunity]
        assert len({row["seed"] for row in rows}) == 1
        for row in rows:
            changed = [key for key in keys if row[key] != {"repetition": 8, "distance": 5,
                       "dictionary_cardinality": 7, "frequency": "uniform", "variation": 3,
                       "variation_type": "mixed", "noise": 2, "exception_rate_permille": 25,
                       "prose_mixture_permille": 150, "target_bytes": 32768}[key]]
            assert len(changed) == 1


def test_distance_is_observed_unrelated_record_gap_and_families_are_not_raw_duplicates():
    for opportunity in inputs.CLASSES:
        diagnostic = inputs.provenance(_spec(opportunity, "strong"))["mechanistic_diagnostics"]
        assert set(diagnostic["measured_intervening_unrelated_record_gaps"]) == {5}
        assert diagnostic["families_with_at_least_three_members"] >= 3
        assert diagnostic["families_with_two_distinct_raw_records"] >= 3
        assert diagnostic["unique_raw_record_fraction_permille"] == 1000


def test_frequency_and_variation_sweeps_change_strong_bytes_not_just_metadata():
    base = _spec("repeated_body_families", "strong")
    assert inputs.generate(base) != inputs.generate({**base, "frequency": "balanced"})
    assert inputs.generate(base) != inputs.generate({**base, "variation_type": "numeric"})
    assert inputs.generate(base) != inputs.generate({**base, "variation_type": "layout"})
    assert inputs.generate(base) != inputs.generate({**base, "distance": 9})
