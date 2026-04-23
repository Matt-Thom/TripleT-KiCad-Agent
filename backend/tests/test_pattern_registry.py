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


from backend.knowledge.registry import PatternRegistry


def test_registry_autodiscovers_all_patterns():
    registry = PatternRegistry.discover()
    ids = {p.metadata.id for p in registry.all()}
    assert "ldo_regulator" in ids
    assert "usb_c_input" in ids
    assert "i2c_pullups" in ids
    assert "mcu_reset" in ids


def test_registry_get_by_id():
    registry = PatternRegistry.discover()
    pat = registry.get("i2c_pullups")
    assert pat is not None
    assert pat.metadata.id == "i2c_pullups"


def test_registry_get_missing_returns_none():
    registry = PatternRegistry.discover()
    assert registry.get("does_not_exist") is None
