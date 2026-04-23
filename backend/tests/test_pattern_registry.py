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


from backend.knowledge.registry import PatternRetriever


def test_retriever_finds_relevant_pattern_for_query():
    registry = PatternRegistry.discover()
    retriever = PatternRetriever(registry)
    hits = retriever.search("3.3V regulator with caps", top_k=3)
    ids = [h.metadata.id for h in hits]
    assert "ldo_regulator" in ids


def test_retriever_finds_i2c_bus_pullups():
    registry = PatternRegistry.discover()
    retriever = PatternRetriever(registry)
    hits = retriever.search("need pullups for my i2c bus", top_k=2)
    ids = [h.metadata.id for h in hits]
    assert "i2c_pullups" in ids


def test_retriever_returns_empty_when_no_match():
    registry = PatternRegistry.discover()
    retriever = PatternRetriever(registry)
    # Query wildly unrelated
    hits = retriever.search("quantum entanglement", top_k=3, min_score=5.0)
    assert hits == []


import asyncio
from backend.services.tools import execute_tool


def test_lookup_pattern_tool_returns_matches():
    result = asyncio.run(execute_tool("lookup_pattern", {"query": "LDO regulator"}))
    assert "ldo_regulator" in result


def test_apply_pattern_tool_returns_download_link(tmp_path, monkeypatch):
    # schematic_service writes to output_dir attribute - so override there
    from backend.services import schematic as sch_mod
    sch_mod.schematic_service.output_dir = str(tmp_path)
    result = asyncio.run(execute_tool("apply_pattern", {
        "pattern_id": "i2c_pullups",
        "inputs": {},
    }))
    assert "Download" in result or "/api/download/" in result
