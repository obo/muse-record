# muse-record

Records **everything** an Interaxon **Muse** EEG headband streams over
Bluetooth LE — the 4 EEG electrodes (plus the AUX channel), the DRL/REF
electrodes, accelerometer, gyroscope, PPG (heart-rate optical sensor) and
battery/telemetry — and streams it as CSV on stdout. The output can be piped
straight into [`live-viewer`](https://github.com/obo/mudrarecord/tree/main/live-viewer)
to plot it live.

`muse-record` talks to the headband directly over BLE (via
[`bleak`](https://github.com/hbldh/bleak) on top of Linux BlueZ). No vendor
app, SDK, account or pairing is needed.

Tested with a **Muse 2** (MU-03, firmware 1.0.21) on Ubuntu 22.04. The Muse
2016 and Muse S (gen 1/2) use the same BLE protocol and should work too (the
2016 model has no PPG). The **Muse S Athena** (gen 3, 2025) uses a different
protocol and is not supported yet (`muse-record` detects it and says so).

## Prerequisites

- Linux with a Bluetooth LE adapter and **BlueZ** (standard on Ubuntu/Debian;
  most laptops' built-in Bluetooth works).
- Python 3.10+ with `venv`.
- Your user must be able to use Bluetooth over D-Bus (the default for a
  desktop user; no `sudo` needed).

On Ubuntu/Debian:

```bash
sudo apt install bluez python3-venv
sudo systemctl enable --now bluetooth      # start the Bluetooth service
bluetoothctl power on                      # make sure the adapter is on
bluetoothctl show | grep Powered           # must say: Powered: yes
```

If `bluetoothctl show` says `No default controller available`, the adapter
is blocked or missing: check `rfkill list` and unblock it with
`rfkill unblock bluetooth`.

## Installation

```bash
git clone <this repository> muse-record
cd muse-record
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

For the live plots, set up `live-viewer` in its own venv (it needs Qt):

```bash
git clone https://github.com/obo/mudrarecord.git
python3 -m venv mudrarecord/live-viewer/venv
mudrarecord/live-viewer/venv/bin/pip install -r mudrarecord/live-viewer/requirements.txt
```

## Connecting to the headband

1. **Turn the headband on**: hold its button until the LEDs light up and
   blink. A blinking Muse is advertising and can be connected to.
2. **Disconnect it from any phone.** A Muse only talks to one device at a time;
   if the Muse app (or Mind Monitor etc.) on your phone is connected to it, close
   the app or switch the phone's Bluetooth off. A Muse that is already connected
   does not show up in scans.
3. Check that the computer can see it:

   ```bash
   ./venv/bin/python muse-record --scan
   # 00:55:DA:B5:86:1D	Muse-861D	-56 dBm
   ```

   Pairing (`bluetoothctl pair`) is **not** needed and not recommended.
4. Optionally check the connection and device status:

   ```bash
   ./venv/bin/python muse-record --info -o /dev/null
   ```

   This prints the headband's firmware version, serial number and battery level
   (`"bp"`) to stderr, records ~2 s and exits.

Without `--address`, `muse-record` uses the first Muse it finds. With several
headbands around, pick one with `--address ADDR` (see `--scan`).

### Troubleshooting

- **`no Muse headband found`**: the headband is off or has gone to sleep (it
  switches itself off after a few minutes of not being connected), or a phone
  is connected to it. Press the button again so it blinks, and retry.
- **Connect attempts fail / time out**: move the headband closer, then reset
  the BlueZ state for it and retry:

  ```bash
  bluetoothctl disconnect <ADDRESS>
  bluetoothctl remove <ADDRESS>    # forgets any stale pairing/cache
  ```

  If that does not help, `sudo systemctl restart bluetooth`.
- **It connects but no data flows**: `muse-record` re-sends its start command
  after 5 s without data. If data still does not come, turn the headband off
  and on again (hold the button until the LEDs go off, then again until they
  blink).
- **EEG values are flat or noisy**: that is contact, not Bluetooth. Wear the
  headband with the forehead sensors and the ear sensors (behind the ears)
  touching skin; moisten them slightly if the skin is dry.

## Usage

Record to a file and watch it live at the same time:

```bash
./venv/bin/python muse-record | tee log.$(date +%Y%m%d-%H%M).csv \
  | mudrarecord/live-viewer/venv/bin/python mudrarecord/live-viewer/live-viewer \
      --width=5s --group=eeg --group=drlref --group=acc --group=gyro --group=ppg
```

Each `--group=<stream>` makes one plot with the columns of that stream (see
below). Use wildcards to show only some columns, e.g. `--group='TP*'` (TP9,
TP10) and `--group='AF*'` (AF7, AF8).

Just record to a file:

```bash
./venv/bin/python muse-record -o recording.csv                 # until Ctrl+C
./venv/bin/python muse-record -o recording.csv --duration 600  # 10 minutes
```

Recording stops on `Ctrl+C`, after `--duration`, or when the headband
disconnects (exit status 1). At the end, a summary is printed to stderr: rows
per stream, packets lost in transmission, and the measured sampling rates.

### Options

| flag | default | meaning |
|---|---|---|
| `--address ADDR` | first Muse found | BLE address of the headband |
| `--scan` | | list nearby Muse headbands and exit |
| `--scan-timeout S` | `10` | seconds to scan |
| `--info` | | print device info/status to stderr, record ~2 s, exit |
| `-o`, `--output FILE` | `-` (stdout) | output CSV file |
| `--duration S` | unlimited | stop after this many seconds |
| `--preset P` | `p50` if the headband has PPG, else `p20` | headband preset (see below) |
| `--skip-eeg`, `--skip-drlref`, `--skip-acc`, `--skip-gyro`, `--skip-ppg`, `--skip-telemetry` | | do not record that stream |
| `--include-seq` | off | add the `seq` column (headband packet counter) |
| `--include-raw-bytes` | off | add a `raw_hex` column with the verbatim BLE packets (implies `--include-seq`); also records any other Muse characteristic `muse-record` has no decoder for |
| `--reorder-latency S` | `0.5` | how long rows are held back so they can be emitted in time order |
| `--verbose`, `-v` | off | extra diagnostics on stderr |

The preset selects what the headband sends. `p50` (the default on a Muse 2 / S)
gives the 4 EEG channels, AUX, and PPG; `p20` gives EEG + AUX without PPG;
`p21` gives only the 4 EEG channels. Accelerometer, gyroscope, DRL/REF and
telemetry are sent with every preset.

## Output format

CSV with a header row; one row per sample of one sensor stream. stdout
carries only the CSV, all messages go to stderr.

```
timestamp_ns, timestamp_iso, stream, [seq,]
TP9, AF7, AF8, TP10, AUX, drl, ref, ax, ay, az, gx, gy, gz,
ppg_ambient, ppg_ir, ppg_red, battery_pct, fuel_gauge_mv, adc_mv, temperature_raw
[, raw_hex]
```

| `stream` | columns | unit | rate (Muse 2) |
|---|---|---|---|
| `eeg` | `TP9, AF7, AF8, TP10` (electrodes: left ear, left forehead, right forehead, right ear), `AUX` (extra channel on the micro-USB port) | µV | 256 Hz |
| `drlref` | `drl, ref` (driven right leg and reference electrodes, centre of forehead) | µV | 28.4 Hz |
| `acc` | `ax, ay, az` | g | 50.8 Hz |
| `gyro` | `gx, gy, gz` | °/s | 50.8 Hz |
| `ppg` | `ppg_ambient, ppg_ir, ppg_red` (optical heart-rate sensor on the forehead) | raw 24-bit counts | 64 Hz |
| `telemetry` | `battery_pct`, `fuel_gauge_mv` (battery voltage), `adc_mv`, `temperature_raw` | | every ~10 s |

- A row fills only the columns of its own `stream`; all others are empty.
  `live-viewer` treats empty values as "no sample", so with `--group=<stream>`
  each plot shows exactly that stream's columns.
- `timestamp_ns` is nanoseconds since the Unix epoch (UTC); `timestamp_iso` is
  the same instant as ISO-8601 UTC. It is the **estimated sampling time of that
  sample**, not the time the packet arrived. The Muse sends samples in packets
  (e.g. 12 EEG samples every 47 ms), and each packet has a sequence number. So
  `muse-record` knows each sample's exact position on the headband's own clock,
  even across lost packets. It measures that clock's actual rate and anchors it
  to the computer's clock using the least delayed packets. Timestamps are
  non-decreasing across the whole file, as `live-viewer` requires.
- Samples lost in transmission are **not** filled in: they show as a gap in the
  timestamps of that stream (and in `seq`). The end-of-recording summary
  counts them.
- EEG is the headband's 12-bit value converted to µV. PPG values are raw
  sensor counts with no unit.
- `seq` (with `--include-seq`) is the headband's 16-bit packet counter; it
  wraps from 65535 to 0.
- `raw_hex` (with `--include-raw-bytes`) is filled on the first row of each
  packet. For `eeg` and `ppg` rows it holds the packets of all channels, in
  column order, separated by `:`.

### Caveats

- The DRL/REF characteristic (`273e0008`) is not documented by Interaxon, and
  other open-source Muse tools do not decode it. `muse-record` reads it as six
  pairs of 12-bit values per packet, scaled like EEG. The data looks
  consistent, but the meaning of the values is a best guess. Use
  `--include-raw-bytes` if you need to reinterpret them later.
- The telemetry `adc_mv` and `temperature_raw` fields read as 0 on the tested
  Muse 2.
- The accelerometer/gyroscope rate is usually quoted as 52 Hz, but the tested
  Muse 2 sends 50.8 Hz. The timestamps use the measured rate.

## Testing

```bash
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest -q
```

The tests check the packet decoders against packets captured from a real
Muse 2, and the timestamping and output ordering. No headband is needed.

## License

MIT
