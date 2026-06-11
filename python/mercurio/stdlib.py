from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StdlibRef:
    qualified_name: str

    @property
    def id(self) -> str:
        return self.qualified_name


# ---------------------------------------------------------------------------
# ISQ quantity-kind value types
# Attributes are typed by *Value definitions spread across ISQ sub-packages.
# ---------------------------------------------------------------------------

_ISQ_MAP: dict[str, str] = {
    # Base quantities (ISQBase)
    "mass": "ISQBase::MassValue",
    "length": "ISQBase::LengthValue",
    "duration": "ISQBase::DurationValue",
    "time": "ISQBase::DurationValue",
    "electric_current": "ISQBase::ElectricCurrentValue",
    "thermodynamic_temperature": "ISQBase::ThermodynamicTemperatureValue",
    "amount_of_substance": "ISQBase::AmountOfSubstanceValue",
    "luminous_intensity": "ISQBase::LuminousIntensityValue",
    # Space / time (ISQSpaceTime)
    "area": "ISQSpaceTime::AreaValue",
    "volume": "ISQSpaceTime::VolumeValue",
    "frequency": "ISQSpaceTime::FrequencyValue",
    "speed": "ISQSpaceTime::SpeedValue",
    "velocity": "ISQSpaceTime::SpeedValue",
    "acceleration": "ISQSpaceTime::AccelerationValue",
    "angular_velocity": "ISQSpaceTime::AngularVelocityValue",
    "angular_acceleration": "ISQSpaceTime::AngularAccelerationValue",
    # Mechanics (ISQMechanics)
    "force": "ISQMechanics::ForceValue",
    "weight": "ISQMechanics::WeightValue",
    "torque": "ISQMechanics::TorqueValue",
    "moment_of_force": "ISQMechanics::TorqueValue",
    "power": "ISQMechanics::PowerValue",
    "momentum": "ISQMechanics::MomentumValue",
    "pressure": "ISQMechanics::PressureValue",
    "stress": "ISQMechanics::StressValue",
    "density": "ISQMechanics::VolumicMassValue",
    # Thermodynamics (ISQThermodynamics)
    "energy": "ISQThermodynamics::EnergyValue",
    "heat": "ISQThermodynamics::HeatValue",
    "entropy": "ISQThermodynamics::EntropyValue",
    "heat_flow_rate": "ISQThermodynamics::HeatFlowRateValue",
    # Electromagnetism (ISQElectromagnetism)
    "electric_potential": "ISQElectromagnetism::ElectricPotentialValue",
    "voltage": "ISQElectromagnetism::ElectricPotentialValue",
    "electric_charge": "ISQElectromagnetism::ElectricChargeValue",
    "capacitance": "ISQElectromagnetism::CapacitanceValue",
    "resistance": "ISQElectromagnetism::ResistanceValue",
    "inductance": "ISQElectromagnetism::InductanceValue",
    "magnetic_flux": "ISQElectromagnetism::MagneticFluxValue",
}


class _ISQNamespace:
    """Maps ISQ quantity-kind names to their *Value stdlib types."""

    def __getattr__(self, name: str) -> StdlibRef:
        key = name.lower()
        if key in _ISQ_MAP:
            return StdlibRef(_ISQ_MAP[key])
        raise AttributeError(
            f"Unknown ISQ quantity '{name}'. "
            f"Use StdlibRef('ISQ<Package>::<Name>Value') for less common quantities."
        )


class _LowercaseNamespace:
    """Maps Python attribute names to stdlib names, keeping lowercase."""

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    def __getattr__(self, name: str) -> StdlibRef:
        return StdlibRef(f"{self._prefix}::{name.lower()}")


class _PascalNamespace:
    """Maps Python attribute names to stdlib names with PascalCase conversion."""

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    def __getattr__(self, name: str) -> StdlibRef:
        return StdlibRef(f"{self._prefix}::{_pascal(name)}")


def _pascal(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in name.split("_") if part)


# Public namespace objects
isq = _ISQNamespace()
si = _LowercaseNamespace("SI")          # SI::kilogram, SI::metre, SI::watt …
scalar_values = _PascalNamespace("ScalarValues")  # ScalarValues::Real, ::String …
