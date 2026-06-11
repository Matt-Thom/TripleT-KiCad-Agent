from backend.services.footprints import map_package_to_footprint


def test_chip_passives_use_reference_prefix():
    assert map_package_to_footprint("0603", reference="R1") == "Resistor_SMD:R_0603_1608Metric"
    assert map_package_to_footprint("0603", reference="C12") == "Capacitor_SMD:C_0603_1608Metric"
    assert map_package_to_footprint("0805", reference="L3") == "Inductor_SMD:L_0805_2012Metric"
    assert map_package_to_footprint("0402", reference="D2") == "Diode_SMD:D_0402_1005Metric"


def test_package_prefixed_chip_size():
    # "R0603" spells the type even without a reference
    assert map_package_to_footprint("R0603") == "Resistor_SMD:R_0603_1608Metric"
    assert map_package_to_footprint("C0402") == "Capacitor_SMD:C_0402_1005Metric"


def test_exact_ic_packages():
    assert map_package_to_footprint("SOT-23", reference="Q1") == "Package_TO_SOT_SMD:SOT-23"
    assert map_package_to_footprint("SOT-23-5", reference="U1") == "Package_TO_SOT_SMD:SOT-23-5"
    assert map_package_to_footprint("SOT-223", reference="U1") == "Package_TO_SOT_SMD:SOT-223-3_TabPin2"
    assert map_package_to_footprint("SOIC-8", reference="U2") == "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"
    assert map_package_to_footprint("LQFP-48", reference="U3") == "Package_QFP:LQFP-48_7x7mm_P0.5mm"
    assert map_package_to_footprint("SOD-123", reference="D1") == "Diode_SMD:D_SOD-123"


def test_annotated_and_lowercase_packages_normalize():
    assert map_package_to_footprint("sot-23(sot-23-3)", reference="U1") == "Package_TO_SOT_SMD:SOT-23"
    assert map_package_to_footprint("soic-8", reference="U1") == "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"


def test_unknown_or_ambiguous_returns_none():
    # Unknown package
    assert map_package_to_footprint("BGA-256", reference="U1") is None
    # Bare chip size with no usable reference: type is ambiguous
    assert map_package_to_footprint("0603") is None
    assert map_package_to_footprint("0603", reference="U1") is None
    # Empty input
    assert map_package_to_footprint("", reference="R1") is None
