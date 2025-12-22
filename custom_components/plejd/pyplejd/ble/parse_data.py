from ..interface.plejd_device import PlejdDeviceType
from .debug import rec_log


def parse_data(data: bytearray, device_types: dict[int, str]):
    data_bytes = [data[i] for i in range(0, len(data))]
    data_hex = "".join(f"{b:02x}" for b in data_bytes)

    match data_bytes:
        case [0x01, 0x01, 0x10, *extra]:
            # Time data
            rec_log(f"TIME DATA {extra}", "TME")
            rec_log(f"    {data_hex}", "TME")

        case [0x02, 0x01, 0x10, 0x00, 0x21, scene, *extra]:
            # Scene update
            rec_log(f"SCENE UPDATE {scene=} {extra=}", "SCN")
            rec_log(f"    {data_hex}", "SCN")
            return {
                "scene": scene,
                "triggered": True,
            }

        case [0x00, 0x01, 0x10, 0x00, 0x21, scene, *extra]:
            # Scene triggered
            rec_log(f"SCENE TRIGGER {scene=} {extra=}", "SCN")
            rec_log(f"    {data_hex}", "SCN")
            return {
                "scene": scene,
                "triggered": True,
            }

        case [0x00, 0x01, 0x10, 0x00, 0x15, *extra]:
            # Identify buttons command
            rec_log(f"IDENTIFY BUTTON REQUEST {extra=}")
            rec_log(f"    {data_hex}")

        case [0x00, 0x01, 0x10, 0x00, 0x16, addr, button, *extra]:
            # Button pressed
            rec_log(f"BUTTON {button=} {extra=}", addr)
            rec_log(f"    {data_hex}", addr)
            return {
                "address": addr,
                "button": button,
                "action": "release" if len(extra) and not extra[0] else "press",
            }

        case [addr, 0x01, 0x10, 0x00, 0xC8, state, data1, data2, *extra] | [
            addr,
            0x01,
            0x10,
            0x00,
            0x98,
            state,
            data1,
            data2,
            *extra,
        ]:
            # State command - different data depending on device type
            extra_hex = "".join(f"{e:02x}" for e in extra)

            result = {
                "address": addr,
                "state": state,
            }
            device_type = device_types.get(addr, None)
            if device_type == PlejdDeviceType.COVER:
                cover_position = int.from_bytes(
                    [data1, data2], byteorder="little", signed=True
                )
                cover_angle = None
                if extra:
                    # The cover angle is given as a six bit signed number?
                    cover_angle = extra[0]
                    cover_angle_sign = 1
                    if cover_angle & 0x20:
                        cover_angle = ~cover_angle
                        cover_angle_sign = -1
                    cover_angle = (cover_angle & 0x1F) * cover_angle_sign
                rec_log(f"    {cover_position=} {cover_angle=}", addr)
                result["cover_position"] = cover_position
                result["cover_angle"] = cover_angle
            elif device_type == PlejdDeviceType.THERMOSTAT:
                # Temperature decoding modulo-64 with 10 degree offset
                current_temperature = (data2 & 0x3F) - 10
                heating = extra[0] == 0x80 # Not sure about this one
                rec_log(f"    {current_temperature=} {heating=}", addr)
                result["current_temperature"] = current_temperature
                result["heating"] = heating
            else: # For some reason, lights seem to have devicetype SENSOR sometimes? So fallback to dimming.
                result["dim"] = data2
                rec_log(f"DIM {state=} {data1=} {data2=} {extra=} {extra_hex}", addr)
                rec_log(f"Unhandled device type {device_type}", addr)

            rec_log(f"    {data_hex}", addr)

            return result

        case [addr, 0x01, 0x10, 0x00, 0x97, state, *extra]:
            # state command
            rec_log(f"STATE {state=} {extra=}", addr)
            rec_log(f"    {data_hex}", addr)
            return {
                "address": addr,
                "state": state,
            }

        case [addr, 0x01, 0x10, 0x04, 0x20, a, 0x01, 0x11, *color_temp]:
            # Color temperature
            color_temp = int.from_bytes(color_temp, "big")
            rec_log(f"COLORTEMP {a}-1-11 {color_temp=}", addr)
            rec_log(f"    {data_hex}", addr)
            return {
                "address": addr,
                "temperature": color_temp,
            }

        case [addr, 0x01, _, 0x04, 0x5c, temp_low, temp_high]:
            # Thermostat target temperature
            # third param is 0x10 when set physically on device, 0x00 or 0x01 when set via Plejd app, 0x03 when responding to our 'AA 0102 045c' request
            temp = int.from_bytes([temp_low, temp_high], "little") / 10
            rec_log(f"THERMOSTAT TARGET TEMP {temp=}", addr)
            rec_log(f"    {data_hex}", addr)
            return {
                "address": addr,
                "target_temperature": temp,
            }

        case [addr, 0x01, _, 0x04, 0x5f, temp_low, temp_high]:
            # Thermostat state update (off)
            rec_log(f"THERMOSTAT STATE OFF", addr)
            rec_log(f"    {data_hex}", addr)
            return {
                "address": addr,
                "state": False,
            }

        case [addr, 0x01, _, 0x04, 0x7e, temp_low, temp_high]:
            # Thermostat state update (on)
            rec_log(f"THERMOSTAT STATE ON", addr)
            rec_log(f"    {data_hex}", addr)
            return {
                "address": addr,
                "state": True,
            }
        
        case [addr, 0x01, _, 0x04, 0x60, sub_id, min_low, min_high, max_low, max_high]:
            # Thermostat temperature limits update
            min_temp = int.from_bytes([min_low, min_high], "little") / 10
            max_temp = int.from_bytes([max_low, max_high], "little") / 10
            rec_log(f"THERMOSTAT LIMITS {min_temp=} {max_temp=}", addr)
            rec_log(f"    {data_hex}", addr)
            return {
                "address": addr,
                "min_temperature": min_temp,
                "max_temperature": max_temp,
            }
        
        case [addr, 0x01, 0x10, 0x04, 0x20, a, 0x03, b, *extra, ll1, ll2]:
            # Motion
            lightlevel = int.from_bytes([ll1, ll2], "big")
            rec_log(f"MOTION {a}-3-{b} {extra=} {lightlevel=}", addr)
            rec_log(f"    {data_hex}", addr)
            return {
                "address": addr,
                "motion": True,
                "luminance": lightlevel,
            }

        case [addr, 0x01, 0x10, 0x04, 0x20, a, 0x05, *extra]:
            # Off by timeout?
            rec_log(f"TIMEOUT {a=}-5 {extra=}", addr)
            rec_log(f"    {data_hex}", addr)

        case [addr, 0x01, 0x10, 0x04, 0x20, *extra]:
            # Unknown new style command
            extra = [f"{e:02x}" for e in extra]
            rec_log(f"UNKNOWN NEW STYLE {addr=} {extra=}", addr)
            rec_log(f"    {data_hex}", addr)

        case [addr, 0x01, 0x10, cmd1, cmd2, *extra]:
            # Unknown command
            cmd = (f"{cmd1:x}", f"{cmd2:x}")
            extra = [f"{e:02x}" for e in extra]
            rec_log(f"UNKNONW OLD COMMAND {addr=} {cmd=} {extra=}", addr)
            rec_log(f"    {data_hex}", addr)

        case _:
            # Unknown command
            rec_log(f"UNKNOWN {data=}")
            rec_log(f"    {data_hex}")

    return {}
