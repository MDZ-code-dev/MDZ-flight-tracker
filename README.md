# MDZ SkyScan

A lightweight pixel-style live aircraft tracker made for **Fedora on Nintendo Switch V1**.

## Current modes

### 1. Nearest Plane
Shows the closest aircraft with:
- Callsign
- Registration
- Aircraft type / description
- ICAO hex
- Altitude
- Ground speed
- Vertical rate
- Heading
- Distance
- Bearing
- Squawk
- Military flag when present in the ADS-B data

### 2. Radar
Shows nearby aircraft as pixel-style contacts around your location and a scrolling contact list.

Use the **MODE** button in the top-right to switch between modes.

## Live data

Aircraft data comes from the public [adsb.lol API](https://api.adsb.lol/docs) and is licensed ODbL.

The app queries aircraft around your saved latitude/longitude. The API supports up to a 250 NM radius.

## Location

Nintendo Switch does not have built-in GPS available to this app. On first launch:

1. Try **USE MY LOCATION** if the browser can provide a network-based location.
2. If that fails, enter latitude and longitude manually.
3. Press **SAVE**.

The coordinates are stored locally in `config.json` on the Switch.

## Install on Fedora Switch

Open **Konsole** and run:

```bash
cd ~
git clone https://github.com/MDZ-code-dev/MDZ-flight-tracker.git
cd MDZ-flight-tracker
chmod +x install.sh start.sh
./install.sh
```

Then open the Fedora application launcher and search for:

```text
MDZ SkyScan
```

No pip packages are required. It uses Python 3's standard library.

## Keep-awake behavior

`start.sh` launches the tracker through `systemd-inhibit` using:

```text
idle:sleep
```

That means Fedora should not automatically idle/sleep while MDZ SkyScan is running.

Closing the app releases the sleep inhibitor, so normal Fedora power management works again.

## Full-screen

The launcher tries, in order:

1. Firefox kiosk mode
2. Chromium full-screen app mode
3. Default browser fallback

## Start manually

```bash
cd ~/MDZ-flight-tracker
./start.sh
```

## Update later

```bash
cd ~/MDZ-flight-tracker
git pull
```

Then launch the app normally again.

## Project layout

```text
MDZ-flight-tracker/
├── app.py          # local Python server + ADS-B API
├── start.sh        # fullscreen + keep-awake launcher
├── install.sh      # Fedora desktop shortcut installer
└── web/
    ├── index.html  # UI
    ├── style.css   # pixel styling
    └── app.js      # mode switch, radar, refresh, settings
```

## Planned ideas

This first version is deliberately easy to expand. More modes and UI ideas can be added to the MODE button later.
