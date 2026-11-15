# Hardware

## The Phase 1 rig

Two identical USB webcam boards are fixed to a steel ruler, facing forward, standing in for
glasses with a camera at each temple.

| Detail | Value |
|---|---|
| Cameras | generic "USB Camera", Sonix chip, `VID_0C45&PID_636B` |
| Spacing | about 11.5 to 12 cm, estimated from a photo. Measure it with a ruler and set `baseline_mm_measured` before calibrating. |
| Left camera | device path fragment `6&1ec6b2f7` (USB port 7) |
| Right camera | device path fragment `6&315a9f63` (USB port 8) |
| Formats | MJPEG up to 1920x1080 at 30 FPS. Uncompressed YUYV only reaches 5 FPS at 1080p and 10 FPS at 720p. |
| Used at | 1280x720 MJPEG, 30 FPS requested |

### Quirks worth knowing

- Both cameras report the same name and the same serial number. Windows tells them apart
  only by the USB port they are in. Move a plug and left and right swap. `sirius check`
  catches this.
- In ordinary room light the boards deliver 25 FPS, not 30. Auto-exposure lengthens each
  frame to 40 ms when light is dim. More light gives 30 FPS.
- The two lens modules are not mounted identically on their circuit boards. With the boards
  level on the ruler, one lens still points about 4 degrees higher and is rolled about 2.2
  degrees. That shows up as a 62 to 65 pixel vertical offset between the images.
  Calibration corrects it in software, but only while nothing moves afterwards. Glue the
  boards down.
- These are night-vision boards: each has a small light sensor that switches on infrared
  LEDs in the dark. In dim light one camera can switch to infrared while the other does not,
  which ruins stereo matching. Test in good light, or tape over the light sensors.
  `sirius check` prints both cameras' colour saturation so a mismatch is visible.
- A camera that another app is using will not open. Close video apps before running SIRIUS.

## Phase 2: wireless sensor node

The next build moves the cameras off the laptop. A Raspberry Pi worn by the user carries
both webcams and an infrared time-of-flight sensor and streams to the laptop over Wi-Fi. Later
the same stream goes to a phone instead. iOS has no driver for USB webcams, so a phone could
never take these cameras by cable; the frames have to arrive over the network either way.

The time-of-flight sensor is an ST VL53L5CX: an 8x8 grid of distances across a 63 degree
view, up to about 4 m, read over I2C. It measures distance directly, so it does not depend
on texture or calibration the way stereo does, and it gives an independent check on the
cameras.

### Parts list

Chosen 2026-11-15 after comparing Amazon India, Robocraze, ThinkRobotics, ElectronicsComp,
Robu.in and Quartz Components. Prices were read from the stores on that date.

| Item | Store | Price (INR) |
|---|---|---|
| Raspberry Pi 5, 4 GB | Robocraze | 13,459 |
| 7Semi ESP32-S3 dev board (N8R8) | Robocraze | 949 |
| Mastech MS830L multimeter | Robocraze | 840 |
| SmartElex VL53L5CX time-of-flight sensor | Robocraze | 765 |
| Noel 7-in-1 soldering kit, 25 W Gold | Robocraze | 499 |
| Official Raspberry Pi 5 Bumper | Robocraze | 224 |
| MB102 830-point breadboard | Robocraze | 66 |
| Jumper wires: female-female, male-male, male-female (40 each) | Robocraze | 142 |
| 40-pin male header strip | Robocraze | 8 |
| Official 27 W USB-C power supply for Pi 5 | Quartz Components | 1,063 |
| Official Raspberry Pi 5 Active Cooler | Quartz Components | 452 |
| **Total** | | **18,467** |

Already owned and reused: the two webcams, a USB pen drive for the Pi's operating system, a
USB-C cable and a power bank.

Notes on the choices:

- The 27 W supply matters. Raspberry Pi's documentation says a Pi 5 on anything less than a
  5 V, 5 A supply limits all its USB ports together to 600 mA, and recommends the 27 W
  supply. Two webcams and a pen drive can exceed 600 mA. On a power bank the limit still
  applies; the documented override is `usb_max_current_enable=1` in
  `/boot/firmware/config.txt`.
- 4 GB rather than 2 GB because the Pi is meant to serve other prototypes too, not only this
  relay. For SIRIUS alone it only forwards frames and 2 GB would do.
- The sensor needs about 90 KB of firmware loaded over I2C every time it powers on. A Pi
  handles that; a small microcontroller with little flash would struggle.
- The sensor listing does not say whether its pins come attached, so the list includes a
  header strip and a soldering kit.
- 60/40 solder contains lead. Solder somewhere ventilated and wash your hands afterwards.
