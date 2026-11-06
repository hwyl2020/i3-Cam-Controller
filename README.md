# Thermal Studio – i3system TE-Q2 / TE-V2 mini

Desktop app to control and live-stream the i3system **TE-Q2** and **TE-V2 mini**
thermal cameras for demos. Dark, presentation-friendly UI built on the official i3system
SDK 2.12.1 (x64, V2 mini build).

## Windows exe (no Python needed)

Build it with `packaging\build_exe.cmd`. It produces:

- `dist\ThermalStudio\ThermalStudio.exe` (keep the whole `ThermalStudio` folder together)
- `dist\ThermalStudio-win64.zip`: copy this to the demo PC, unzip it, and run `ThermalStudio.exe`

The exe bundles Python, Qt, the i3system SDK DLLs and the Visual C++/MFC
runtime they need. The demo PC only needs the i3system **T.E USB driver**.
Captures default to `Documents\Thermal Studio` (change it with **Browse…**).

## Run from source

Double-click **`run.cmd`**, or:

```
python app\main.py
```

Requirements: Windows 10/11 x64, Python 3.10+ and the i3system **T.E USB driver**.
`run.cmd` installs the Python packages from `requirements.txt` if missing.
The prebuilt SDK bridge (`app\bin\te_bridge.dll`) is included; to rebuild it
run `bridge\build.cmd` (needs Visual Studio with C++ tools).

## Features

| Area | What you can demo |
|---|---|
| Live view | Real-time thermal stream, FPS, resolution, timestamp overlay |
| Palettes | All 10 SDK palettes (White Hot, Black Hot, Iron, Blue-Red, Medical, Purple, Purple-Yellow, Dark Blue, Cyan, Rainbow) |
| Range | Auto AGC, linear auto range, manual min/max lock with true-temperature colour bar |
| Image | Temporal & spatial noise filters, edge enhancement, i3 image enhancement, mirror/flip, 1×/2×/4× zoom |
| Measurement | Live max / min / centre / scene average, hot & cold spot markers, up to 6 pinned spots (click), measurement area (drag), cursor readout, °C/°F |
| Emissivity | 0.10–1.00 slider with material presets |
| Alarm | Highlights pixels above a threshold + flashing banner |
| Calibration | Flat-field NUC, lens offset calibration, bad-pixel detection, save/load calibration |
| Auto shutter | TE-V2 mini (and V2): periodic, on temperature change, or manual |
| Capture | PNG snapshot (with overlays) + per-pixel temperature CSV, MP4 recording |
| Presentation | Full screen with controls hidden (`F11`, `Esc` to exit) – ideal for screen-sharing in Teams/Zoom |
| Simulator | Built-in synthetic TE-Q2 so the UI can be shown without hardware |

### Keyboard shortcuts

`Space` pause · `S` snapshot · `R` record · `P` next palette · `1` `2` `4` zoom ·
`C` clear marks · `F11` presentation · `Esc` exit presentation

Captures are saved in `captures\`.

## Connecting the camera

1. Install the **T.E USB driver** from i3system and plug the camera directly
   into a USB 3 port (no hub).
2. Press **Scan**, pick the entry for **your** model (or *TE-Q2 / TE-V2 mini direct
   open · USB #0*), press **Connect**. The scan cannot tell Type B models apart, so each
   detected camera is listed once per model; the model you used last is listed first.
   Opening takes a few seconds while the camera's calibration is read from flash.

### TE-Q2 behaviour notes (verified on hardware)

- Windows shows it as **i3system USB Device** (`VID_0547&PID_0080`). Opening takes ~8 s.
- It streams **384×288 at ~9 fps**. Between frames the SDK's `RecvImage` returns
  code 4 ("data read fail") or 2 – these are polling misses, not errors (the
  sample-app log entries with code 4 are the same thing). The app only reports
  an error if no frame arrives for 12 s.
- USB scan finds the camera but reports model 0, so the app assumes TE-Q2.
- Serial number, firmware version and FPA (sensor) temperature are not reported
  by the TE-Q2 through this SDK, so they are shown as "—" / hidden.
- `CloseTE()` must not be followed by deleting the `TE_B` object (crashes).

### TE-V2 mini notes (verified on hardware)

- Needs the **V2 mini build of SDK 2.12.1** (`windows-x64-p-2.12.1`, the DLLs now in
  `app/bin`): its `i3system_TE_x64.dll` has the V2 mini packet decoder
  (`CPacketStrategyV2Mini`). The earlier 2.12.1 x64 DLL lacked it and could only deliver
  uncorrected raw frames without temperatures.
- Shows up with the same USB ID as the TE-Q2 (`VID_0547&PID_0080`) and the scan reports
  model 0, so pick the **TE-V2 mini** entry. Opened as a TE-Q2 it "streams" garbage.
- Opening takes ~11 s. Streams **640×480 at 30 fps with temperatures** (`RecvImage` with
  AGC + `CalcEntireTemp`). Firmware version and a numeric serial number are reported;
  the FPA temperature (around -13 °C) is not plausible and is hidden.
- The SDK's output pipeline (`SetImgOutPrms`: noise filters, edge) and the raw float
  frame used by i3 enhancement return -11 on the V2 mini, so for it the app does the
  temporal / spatial noise filters, edge enhancement and local contrast (CLAHE) itself,
  and stretches the SDK's AGC image, which only fills part of the 16-bit range.
- NUC (`ShutterCalibrationOn`, 0.5 s) and the **Auto shutter** settings (periodic /
  on temperature change / manual) are accepted by the camera.
- Disconnect before closing the app – closing mid-stream can leave the camera stuck
  until it is replugged.

## Project layout

```
bridge/        te_bridge.cpp – flat C wrapper over the SDK's C++ TE_B class; build.cmd
app/main.py    entry point
app/core/      sdk.py (ctypes binding + camera), simulator.py, engine.py (acquisition
               thread), palettes.py, recorder.py
app/ui/        main_window.py, video_view.py (image + overlays), widgets.py, theme.py
app/bin/       te_bridge.dll + i3system SDK runtime DLLs (incl. OpenCV 2.4.9 it depends on)
sdk/           i3system SDK 2.12.1 headers and x64 import libraries (for building the bridge)
```

The i3system SDK files are © i3system Inc., distributed under the licence
stated in the SDK headers (CC-BY-4.0).
