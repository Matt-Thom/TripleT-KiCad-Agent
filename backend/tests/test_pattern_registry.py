from backend.knowledge.protocol import Pattern, PatternMetadata


def test_pattern_metadata_has_required_fields():
    md = PatternMetadata(
        id="ldo_regulator",
        title="Fixed-output LDO regulator",
        tags=["power", "regulator", "ldo"],
        description="A fixed LDO with input/output decoupling caps.",
        inputs={"ldo_mpn": "STR", "cin": "STR", "cout": "STR"},
    )
    assert md.id == "ldo_regulator"
    assert "power" in md.tags


def test_pattern_protocol_has_metadata_and_apply():
    # Structural check — any class with metadata: PatternMetadata and apply(sch, **inputs) is a Pattern.
    class Dummy:
        metadata = PatternMetadata(
            id="x", title="x", tags=[], description="", inputs={}
        )

        def apply(self, sch, **inputs):
            return sch

    # Runtime-checkable protocol:
    from backend.knowledge.protocol import is_pattern
    assert is_pattern(Dummy())
