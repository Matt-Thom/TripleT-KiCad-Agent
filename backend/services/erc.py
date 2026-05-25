from typing import List, Dict
from pydantic import BaseModel
from backend.models.schematic_ir import SchematicIRData, ComponentInstance

class ErcViolation(BaseModel):
    severity: str  # "ERROR" or "WARNING"
    rule: str      # E.g. "FLOATING_INPUT", "POWER_CONFLICT", "MISSING_DECOUPLING", "MISSING_PULLUP"
    message: str
    elements: List[str]  # References or Net Names involved

class ElectricalRuleChecker:
    def check(self, ir: SchematicIRData) -> List[ErcViolation]:
        violations: List[ErcViolation] = []
        
        # Build pin map for fast lookup: (ref, pin_num) -> PinSpec
        pin_map = {}
        component_map = {c.reference: c for c in ir.components}
        for comp in ir.components:
            for p in comp.pins:
                pin_map[(comp.reference, p.number)] = p

        # Build net map for lookup: (ref, pin_num) -> list of net names
        pin_to_nets: Dict[tuple[str, str], List[str]] = {}
        for net in ir.nets:
            for conn in net.connections:
                pin_to_nets.setdefault((conn.component_ref, conn.pin_number), []).append(net.name)

        # 1. Check Floating Inputs
        for comp in ir.components:
            for p in comp.pins:
                if p.type == "input":
                    nets = pin_to_nets.get((comp.reference, p.number), [])
                    if not nets:
                        violations.append(ErcViolation(
                            severity="WARNING",
                            rule="FLOATING_INPUT",
                            message=f"Pin {p.number} ({p.name}) of {comp.reference} is an input but not connected to any net.",
                            elements=[f"{comp.reference}.{p.number}"]
                        ))
                    else:
                        # Connected, but is there a driver on the net?
                        has_driver = False
                        for net_name in nets:
                            net_conns = next((n.connections for n in ir.nets if n.name == net_name), [])
                            for conn in net_conns:
                                connected_pin = pin_map.get((conn.component_ref, conn.pin_number))
                                if connected_pin and connected_pin.type in ("output", "power_out", "bidirectional"):
                                    has_driver = True
                                    break
                            if has_driver:
                                break
                        if not has_driver:
                            violations.append(ErcViolation(
                                severity="WARNING",
                                rule="NO_DRIVER",
                                message=f"Input pin {comp.reference}.{p.number} ({p.name}) is connected to net '{nets[0]}' but has no driving source (output/power_out/bidirectional).",
                                elements=[f"{comp.reference}.{p.number}", nets[0]]
                            ))

        # 2. Check Power Conflicts (e.g. driving same power rail)
        for net in ir.nets:
            power_out_drivers = []
            for conn in net.connections:
                p = pin_map.get((conn.component_ref, conn.pin_number))
                if p and p.type == "power_out":
                    power_out_drivers.append(f"{conn.component_ref}.{conn.pin_number}")
            if len(power_out_drivers) > 1:
                violations.append(ErcViolation(
                    severity="ERROR",
                    rule="POWER_CONFLICT",
                    message=f"Net '{net.name}' is driven by multiple power output pins: {', '.join(power_out_drivers)}.",
                    elements=[net.name] + power_out_drivers
                ))

        # 3. Check Decoupling Caps for ICs
        for comp in ir.components:
            # Heuristic: ICs usually have references starting with 'U'
            if comp.reference.startswith("U"):
                power_pins = [p for p in comp.pins if p.type == "power_in"]
                for p in power_pins:
                    nets = pin_to_nets.get((comp.reference, p.number), [])
                    if not nets:
                        continue
                    net_name = nets[0]
                    
                    # Ignore if the net name is GND (GND is reference, not power rail)
                    if "GND" in net_name.upper():
                        continue

                    # Check if there is a decoupling cap connected to this power net and a GND net
                    has_decoupling = False
                    for other_comp in ir.components:
                        if other_comp.reference.startswith("C"):
                            # Decoupling cap needs to be connected to the power net and a GND net
                            cap_nets = [pin_to_nets.get((other_comp.reference, p_num), []) for p_num in ("1", "2")]
                            flat_cap_nets = [n for sub in cap_nets for n in sub]
                            if net_name in flat_cap_nets and any("GND" in n.upper() for n in flat_cap_nets):
                                has_decoupling = True
                                break
                    if not has_decoupling:
                        violations.append(ErcViolation(
                            severity="WARNING",
                            rule="MISSING_DECOUPLING",
                            message=f"No decoupling capacitor detected for IC power pin {comp.reference}.{p.number} ({p.name}) on net '{net_name}'.",
                            elements=[f"{comp.reference}.{p.number}", net_name]
                        ))

        # 4. Check Pull-Ups on I2C Lines
        for net in ir.nets:
            if "SDA" in net.name.upper() or "SCL" in net.name.upper():
                # Check for pull-up resistor to a high power rail (e.g. 3V3, 5V, VDD)
                has_pullup = False
                for conn in net.connections:
                    if conn.component_ref.startswith("R"):
                        res = component_map.get(conn.component_ref)
                        if res:
                            other_pin = "2" if conn.pin_number == "1" else "1"
                            other_nets = pin_to_nets.get((res.reference, other_pin), [])
                            if other_nets and any(n.upper() in ("3V3", "5V", "VDD") for n in other_nets):
                                has_pullup = True
                                break
                if not has_pullup:
                    violations.append(ErcViolation(
                        severity="WARNING",
                        rule="MISSING_PULLUP",
                        message=f"I2C Net '{net.name}' is missing a pull-up resistor to VDD.",
                        elements=[net.name]
                    ))

        return violations

erc_service = ElectricalRuleChecker()
