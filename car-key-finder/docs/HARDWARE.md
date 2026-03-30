# Car Key Finder — Hardware Guide

## Shopping List

| Part | Model | ~Cost | Purpose |
|------|-------|-------|---------|
| Microcontroller | ESP32 DevKit v1 | $8 | Brain of the device |
| Sub-GHz transceiver | CC1101 module (SPI) | $5 | Listen for key fob response on 315/433 MHz |
| Inductor coil | 125 kHz antenna coil (1mH) | $3 | Send LF wake-up pulse to smart key |
| MOSFET | IRLZ44N (logic-level) | $1 | Drive the LF coil |
| Buzzer | Active piezo buzzer 3.3V | $1 | Audio proximity feedback |
| LEDs | 3x LEDs (green/yellow/red) | $1 | Visual proximity indicator |
| Resistors | 3x 220 ohm, 1x 10K | $1 | LED current limiting, MOSFET pulldown |
| Battery | 3.7V LiPo 500mAh + TP4056 charger | $4 | Portable power |
| Button | Momentary push button | $0.50 | Trigger scan |
| **Total** | | **~$25** | |

## Wiring

```
ESP32 Pin Connections:
----------------------------------------------
GPIO 18 (SCK)   --> CC1101 SCLK
GPIO 23 (MOSI)  --> CC1101 MOSI
GPIO 19 (MISO)  --> CC1101 MISO
GPIO  5 (SS)    --> CC1101 CSN
GPIO  2 (GDO0)  --> CC1101 GDO0

GPIO 25         --> MOSFET gate (drives 125kHz coil)
                    MOSFET drain --> coil --> 3.3V
                    MOSFET source --> GND
                    10K resistor gate --> GND

GPIO 26         --> Buzzer (+)
GPIO 32         --> Green LED --> 220ohm --> GND
GPIO 33         --> Yellow LED --> 220ohm --> GND
GPIO 27         --> Red LED --> 220ohm --> GND

GPIO  4         --> Scan button --> GND (use internal pullup)
```

## How It Works

```
┌─────────┐   125 kHz pulse   ┌──────────┐
│  Device  │ ───────────────▶  │ Car Key  │
│ (ESP32)  │                   │ (Smart)  │
│          │  ◀─────────────── │          │
│          │   315/433 MHz     │          │
│  CC1101  │   response        └──────────┘
│  ▼       │
│  RSSI ──▶ buzzer beep rate
│          ▶ LED bar
└─────────┘
```

1. Press the button
2. ESP32 pulses the 125 kHz coil (mimics the car's LF antenna)
3. If the smart key is in range, it wakes up and transmits a UHF response
4. CC1101 receives the response and reports RSSI (signal strength)
5. Stronger signal = faster beep + more LEDs lit = you're getting closer
