# Västtrafik Departures Display

A Python-based real-time departures display for Västtrafik stops.

## Setup

1. **Get API credentials:**
   - Go to https://developer.vasttrafik.se/
   - Register and create an application
   - Get your Client ID and Client Secret

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your credentials
   ```

## Usage

### Search for your stop:
```bash
python display_departures.py --search "Brunnsparken"
```

This will show you the stop names and their GIDs (Global IDs).

### Display departures for a specific stop:
```bash
python display_departures.py --stop-id "9021014001960000"
```

### Use .env configuration:
Add your `STOP_ID` to the `.env` file, then simply run:
```bash
python display_departures.py
```

## Next Steps

- Add auto-refresh functionality
- Create a web interface (Flask/HTML)
- Add support for multiple stops
- Create a GUI with tkinter or PyQt
- Deploy on a Raspberry Pi with a display

## API Documentation

- Västtrafik Developer Portal: https://developer.vasttrafik.se/
- API Documentation: https://developer.vasttrafik.se/portal/#/api
