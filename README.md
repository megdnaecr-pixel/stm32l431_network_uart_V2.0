# STM32L431 Network CAN V2.0

Firmware for the **STM32L431CC** microcontroller that acts as a CAN-bus command relay node. It receives framed commands over CAN, validates them with CRC-16, drives GPIO outputs accordingly, and sends an ACK back on the bus.

## Hardware

| Peripheral | Pins | Notes |
|------------|------|-------|
| CAN1 | PB8 (RX), PB9 (TX) | 500 kbps, standard frames, via UT82 transceiver |
| GPIO1 | PA9 | Output channel 1 |
| GPIO2 | PA10 | Output channel 2 |
| GPIO3 | PA4 | Output channel 3 |
| GPIO4 | PA5 | Output channel 4 |
| LED1 | PB6 | Output channel 5 / status indicator |

- CAN transceiver: VATU501/CM_118 with ESD protection (BSD5C051V) and common-mode choke (DLW43MH201XK2L)
- Power: 28V -> 5V buck (MP62051) -> 3.3V LDO (MAX6219)
- System clock: 80 MHz (HSI 16 MHz + PLL)

## Protocol

Every CAN frame carries a 5-byte payload:

```
[0xCC] [0xBA] [CMD] [CRC_L] [CRC_H]
```

- **0xCC 0xBA** -- fixed header
- **CMD** -- command byte (see table below)
- **CRC_L / CRC_H** -- CRC-16 (polynomial 0x1021) over the first 3 bytes, masked to 14 bits

### Supported commands

| Command | Value | Output Pin | Action |
|---------|-------|-----------|--------|
| CMD_1_On / CMD_1_Off | 0x01 / 0x02 | GPIO1 (PA9) | Channel 1 on/off |
| CMD_2_On / CMD_2_Off | 0x03 / 0x04 | GPIO2 (PA10) | Channel 2 on/off |
| CMD_3_On / CMD_3_Off | 0x05 / 0x06 | GPIO3 (PA4) | Channel 3 on/off |
| CMD_4_On / CMD_4_Off | 0x07 / 0x08 | GPIO4 (PA5) | Channel 4 on/off |
| CMD_5_On / CMD_5_Off | 0x09 / 0x0A | LED1 (PB6) | Channel 5 on/off |

On commands set the output HIGH; Off commands set it LOW. After executing a command the node transmits an ACK frame (same protocol) on CAN ID `0x100`.

## Testing

`can_test.py` is a Python script (requires `python-can`) that talks to the board via a USB-to-CAN (SLCAN) adapter:

```bash
pip install python-can pyserial
python can_test.py --channel /dev/ttyACM0
```

## Building

Open the project in **STM32CubeIDE** (or any arm-none-eabi-gcc toolchain) and build the `Debug` configuration. The `.cproject` and `.project` files are in `stm32l431_network_uart_V1.0/stm32l431_network_uart/`.

## License

See individual driver files for STMicroelectronics license terms.
