# SIRIUS

> **Research prototype. Not a safety device.** It supplements a white cane; it does not replace one.

Two matched webcams on a rigid rig measure distance by stereo, a detector names what is in
front, and the laptop speaks short alerts: "person, one metre, ahead".

## Setup

```
uv sync
uv run sirius devices
```

Cameras are bound by DirectShow device path in `config/rig.toml`. Both report the name
"USB Camera"; the path fragment is tied to the USB port.

## Licences of models used

- D-FINE (`ustc-community/dfine-small-coco`) — Apache-2.0
- Fast-FoundationStereo (`nvidia/c-fast-foundationstereo`) — NVIDIA Open Model Agreement
- Depth Anything V2 metric (benchmark only) — see its model card
