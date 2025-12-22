"""Support for Plejd thermostats."""

from homeassistant.components.climate import ClimateEntity, HVACMode, ClimateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .plejd_site import dt, get_plejd_site_from_config_entry
from .plejd_entity import PlejdDeviceBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Plejd thermostats from a config entry."""
    site = get_plejd_site_from_config_entry(hass, config_entry)

    @callback
    def async_add_thermostat(device: dt.PlejdThermostat) -> None:
        """Add thermostat from Plejd."""
        entity = PlejdThermostat(device)
        async_add_entities([entity])

    site.register_platform_add_device_callback(
        async_add_thermostat, dt.PlejdDeviceType.THERMOSTAT
    )


class PlejdThermostat(PlejdDeviceBaseEntity, ClimateEntity):
    """Representation of a Plejd thermostat."""

    def __init__(self, device: dt.PlejdThermostat) -> None:
        """Set up thermostat."""
        ClimateEntity.__init__(self)
        PlejdDeviceBaseEntity.__init__(self, device)
        self.device: dt.PlejdThermostat

        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
        self._attr_temperature_unit = "°C"
        self._attr_min_temp = device.minTemperature
        self._attr_max_temp = device.maxTemperature
        self._attr_target_temperature_step = 1.0

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._data.get("current_temperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._data.get("target_temperature")

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if min_t := self._data.get("min_temperature"):
            return min_t
        return self._attr_min_temp

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if max_t := self._data.get("max_temperature"):
            return max_t
        return self._attr_max_temp

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if self._data.get("state", False):
            return HVACMode.HEAT
        return HVACMode.OFF

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is not None:
            await self.device.set_temperature(temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        mode_str = "heat" if hvac_mode == HVACMode.HEAT else "off"
        await self.device.set_hvac_mode(mode_str)

    async def async_turn_off(self) -> None:
        """Turn off the thermostat."""
        await self.async_set_hvac_mode(HVACMode.OFF)
    
    async def async_turn_on(self) -> None:
        """Turn on the thermostat."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    def _handle_update(self, data) -> None:
        """Handle updates from the device."""
        if data.get("available") and "target_temperature" not in self._data:
            # Request target temperature if device is available and we don't know it yet
            self.hass.async_create_task(self.device.request_target_temperature())