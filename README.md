# STM32L431 Network UART V2.0

Firmware for the **STM32L431CC** microcontroller that acts as a CAN-bus command relay node. It receives framed commands over CAN, validates them with CRC-16, drives a GPIO output accordingly, and sends an ACK back on the bus.

## Hardware

| Peripheral | Pins | Notes |
|------------|------|-------|
| CAN1 | PB8 (RX), PB9 (TX) | 500 kbps, standard frames |
| USART2 | PA2 (TX), PA3 (RX) | 115200 baud, DMA-backed |
| USART3 | PB10 (TX), PB11 (RX) | 115200 baud |
| LED1 | PB6 | Command status indicator |

System clock: 80 MHz (HSI 16 MHz + PLL).

## Protocol

Every CAN frame carries a 5-byte payload:

```
[0xCC] [0xBA] [CMD] [CRC_L] [CRC_H]
```

- **0xCC 0xBA** -- fixed header
- **CMD** -- command byte (see table below)
- **CRC_L / CRC_H** -- CRC-16 (polynomial 0x1021) over the first 3 bytes, masked to 14 bits

### Supported commands

| Command | Value | Action |
|---------|-------|--------|
| CMD_1_On / CMD_1_Off | 0x01 / 0x02 | Channel 1 control |
| CMD_2_On / CMD_2_Off | 0x03 / 0x04 | Channel 2 control |
| CMD_3_On / CMD_3_Off | 0x05 / 0x06 | Channel 3 control |
| CMD_4_On / CMD_4_Off | 0x07 / 0x08 | Channel 4 control |
| CMD_5_On / CMD_5_Off | 0x09 / 0x0A | Channel 5 control |
| CMD_6_On / CMD_6_Off | 0x0B / 0x0C | Channel 6 control |
| CMD_7_On / CMD_7_Off | 0x0E / 0x0D | Channel 7 control |
| CMD_8_Off | 0x0F | Channel 8 off-only |
| CMD_9_On / CMD_9_Off | 0x11 / 0x10 | Channel 9 control |

On commands set LED1 HIGH; Off commands set it LOW. After executing a command the node transmits an ACK frame (same protocol) on CAN ID `0x100`.

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
