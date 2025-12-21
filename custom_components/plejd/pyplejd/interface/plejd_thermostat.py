from .plejd_device import PlejdOutput, PlejdTraits, PlejdDeviceType


class PlejdThermostat(PlejdOutput):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.outputType = PlejdDeviceType.THERMOSTAT
        self.minTemperature = self.settings.climateSettings.temperatureLimits.minUserInputTemperature
        self.maxTemperature = self.settings.climateSettings.temperatureLimits.maxUserInputTemperature

    def parse_state(self, update, state):
        available = state.get("available", False)
        return {
            "available": available,
            "current_temperature": state.get("current_temperature", None),
            "target_temperature": state.get("target_temperature", None),
            "state": state.get("state", False),
            "min_temperature": state.get("min_temperature", None),
            "max_temperature": state.get("max_temperature", None),
        }

    async def set_temperature(self, temperature):
        if not self._mesh:
            return
        temp_value = int(temperature)
        await self._mesh.set_state(self.address, target_temperature=temp_value)

    async def set_hvac_mode(self, hvac_mode):
        if not self._mesh:
            return
        state = hvac_mode == "heat"
        await self._mesh.set_state(self.address, state=state)

    async def request_target_temperature(self):
        if not self._mesh:
            return
        await self._mesh.request_target_temperature(self.address)