import pytest
from backend.models.schematic_ir import SchematicIRData, ComponentInstance, NetConnection, PinRef
from backend.services.procedural_symbol import PinSpec
from backend.services.erc import erc_service

def test_erc_floating_input():
    # U1 has an input pin that is not connected
    comp = ComponentInstance(
        reference="U1",
        mpn="TEST_MCU",
        supplier_id="C123",
        pins=[PinSpec(number="1", name="IN", type="input")]
    )
    ir = SchematicIRData(components=[comp], nets=[])
    violations = erc_service.check(ir)
    
    assert len(violations) == 1
    assert violations[0].rule == "FLOATING_INPUT"
    assert violations[0].severity == "WARNING"


def test_erc_no_driver():
    # U1 pin 1 (input) is connected to net 'SIG', but there is no driver
    comp = ComponentInstance(
        reference="U1",
        mpn="TEST_MCU",
        supplier_id="C123",
        pins=[PinSpec(number="1", name="IN", type="input")]
    )
    net = NetConnection(
        name="SIG",
        connections=[PinRef(component_ref="U1", pin_number="1")]
    )
    ir = SchematicIRData(components=[comp], nets=[net])
    violations = erc_service.check(ir)
    
    assert len(violations) == 1
    assert violations[0].rule == "NO_DRIVER"


def test_erc_power_conflict():
    # Two LDOs (U1, U2) drive the same '3V3' rail
    ldo1 = ComponentInstance(
        reference="U1",
        mpn="LDO",
        supplier_id="C1",
        pins=[PinSpec(number="2", name="VOUT", type="power_out")]
    )
    ldo2 = ComponentInstance(
        reference="U2",
        mpn="LDO",
        supplier_id="C2",
        pins=[PinSpec(number="2", name="VOUT", type="power_out")]
    )
    net = NetConnection(
        name="3V3",
        connections=[
            PinRef(component_ref="U1", pin_number="2"),
            PinRef(component_ref="U2", pin_number="2")
        ]
    )
    ir = SchematicIRData(components=[ldo1, ldo2], nets=[net])
    violations = erc_service.check(ir)
    
    assert any(v.rule == "POWER_CONFLICT" for v in violations)


def test_erc_missing_decoupling():
    # U1 has a power_in pin on '3V3' net, but there's no capacitor
    comp = ComponentInstance(
        reference="U1",
        mpn="MCU",
        supplier_id="C123",
        pins=[
            PinSpec(number="1", name="VDD", type="power_in"),
            PinSpec(number="2", name="GND", type="power_in"),
            PinSpec(number="3", name="IN", type="input")
        ]
    )
    # Add a driver so NO_DRIVER doesn't fire
    driver = ComponentInstance(
        reference="U2",
        mpn="LDO",
        supplier_id="C456",
        pins=[PinSpec(number="1", name="OUT", type="power_out")]
    )
    net_power = NetConnection(
        name="3V3",
        connections=[
            PinRef(component_ref="U1", pin_number="1"),
            PinRef(component_ref="U2", pin_number="1")
        ]
    )
    net_gnd = NetConnection(
        name="GND",
        connections=[PinRef(component_ref="U1", pin_number="2")]
    )
    ir = SchematicIRData(components=[comp, driver], nets=[net_power, net_gnd])
    violations = erc_service.check(ir)
    
    assert any(v.rule == "MISSING_DECOUPLING" for v in violations)


def test_erc_missing_pullup():
    # I2C lines SDA and SCL connected between U1 and U2 but no pullup resistor
    mcu = ComponentInstance(
        reference="U1",
        mpn="MCU",
        supplier_id="C1",
        pins=[
            PinSpec(number="1", name="SDA", type="bidirectional"),
            PinSpec(number="2", name="SCL", type="bidirectional")
        ]
    )
    sensor = ComponentInstance(
        reference="U2",
        mpn="SENSOR",
        supplier_id="C2",
        pins=[
            PinSpec(number="1", name="SDA", type="bidirectional"),
            PinSpec(number="2", name="SCL", type="bidirectional")
        ]
    )
    net_sda = NetConnection(
        name="I2C_SDA",
        connections=[
            PinRef(component_ref="U1", pin_number="1"),
            PinRef(component_ref="U2", pin_number="1")
        ]
    )
    net_scl = NetConnection(
        name="I2C_SCL",
        connections=[
            PinRef(component_ref="U1", pin_number="2"),
            PinRef(component_ref="U2", pin_number="2")
        ]
    )
    ir = SchematicIRData(components=[mcu, sensor], nets=[net_sda, net_scl])
    violations = erc_service.check(ir)
    
    assert any(v.rule == "MISSING_PULLUP" for v in violations)
