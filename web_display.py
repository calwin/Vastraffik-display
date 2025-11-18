#!/usr/bin/env python3
"""
Västtrafik Departures Web Display
A web interface optimized for TV viewing.
"""

import os
from flask import Flask, render_template, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
from vasttrafik_api import VasttrafikAPI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


def format_time(departure_time_str):
    """Format departure time - returns tuple of (relative_time, actual_time)."""
    try:
        # Clean up the timestamp - remove excessive microseconds and handle timezone
        import re
        # Replace .0000000 with .000000 (max 6 digits for microseconds)
        clean_time = re.sub(r'\.(\d{7,})', lambda m: '.' + m.group(1)[:6], departure_time_str)
        clean_time = clean_time.replace('Z', '+00:00')

        dept_time = datetime.fromisoformat(clean_time)
        now = datetime.now(dept_time.tzinfo)
        diff = (dept_time - now).total_seconds() / 60

        # Get the actual time HH:MM
        actual_time = dept_time.strftime("%H:%M")

        if diff < 1:
            relative_time = "Now"
        elif diff < 60:
            relative_time = f"{int(diff)} min"
        else:
            # Show hours for longer waits
            hours = int(diff / 60)
            if hours == 1:
                relative_time = "1 hour"
            else:
                relative_time = f"{hours} hours"

        return relative_time, actual_time
    except Exception as e:
        # If parsing fails, try to extract HH:MM from the string
        if 'T' in departure_time_str:
            try:
                return "-", departure_time_str.split('T')[1][:5]
            except:
                pass
        return "-", departure_time_str


@app.route('/')
def index():
    """Display the departures board."""
    return render_template('departures.html')


@app.route('/api/voice')
def get_voice_departures():
    """API endpoint for voice assistants - returns simple text response."""
    stop_id = os.getenv('STOP_ID')

    if not stop_id:
        return jsonify({'speech': 'Stop ID not configured.'}), 400

    try:
        api = VasttrafikAPI()
        data = api.get_departures(stop_id, limit=3)  # Get next 3 departures (shorter for voice)

        # Get stop name
        stop_name = "your stop"
        if 'results' in data and len(data['results']) > 0:
            first_result = data['results'][0]
            stop_name = first_result.get('stopPoint', {}).get('name', 'your stop')
            stop_name = stop_name.replace(', Göteborg', '').replace(', Goteborg', '')

        # Build voice response
        speech_parts = [f"Next departures from {stop_name}:"]

        if 'results' in data and data['results']:
            for i, dep in enumerate(data['results'][:3], 1):
                line_info = dep.get('serviceJourney', {}).get('line', {})
                line = line_info.get('shortName', 'unknown')
                direction = dep.get('serviceJourney', {}).get('direction', 'unknown destination')
                transport_mode = line_info.get('transportMode', 'bus')

                # Get times
                estimated_time_str = dep.get('estimatedTime', '')
                relative_time, actual_time = format_time(estimated_time_str) if estimated_time_str else ('-', '-')

                # Check status
                is_delayed = dep.get('estimatedTime') and dep.get('estimatedTime') != dep.get('plannedTime')
                is_cancelled = dep.get('isCancelled', False)

                track = dep.get('stopPoint', {}).get('platform', 'unknown platform')

                # Build sentence
                vehicle = "Tram" if transport_mode == "tram" else "Bus"

                if is_cancelled:
                    sentence = f"{vehicle} {line} to {direction} is cancelled."
                else:
                    delay_text = ", delayed" if is_delayed else ""
                    sentence = f"{vehicle} {line} to {direction} in {relative_time} at platform {track}{delay_text}."

                speech_parts.append(sentence)
        else:
            speech_parts.append("No departures found.")

        speech_text = " ".join(speech_parts)

        return jsonify({
            'speech': speech_text,
            'displayText': speech_text,
            'stopName': stop_name
        })

    except Exception as e:
        return jsonify({'speech': f'Error getting departures: {str(e)}'}), 500


def normalize_swedish(text):
    """Normalize Swedish characters for English pronunciation."""
    replacements = {
        'å': 'o',
        'ä': 'a',
        'ö': 'o',
        'Å': 'O',
        'Ä': 'A',
        'Ö': 'O'
    }
    for swedish, english in replacements.items():
        text = text.replace(swedish, english)
    return text


@app.route('/api/voice/text')
def get_voice_text():
    """Returns plain text for easier IFTTT integration."""
    stop_id = os.getenv('STOP_ID')

    if not stop_id:
        return 'Stop ID not configured.', 400

    try:
        api = VasttrafikAPI()
        data = api.get_departures(stop_id, limit=10)

        # Get stop name
        stop_name = "your stop"
        if 'results' in data and len(data['results']) > 0:
            first_result = data['results'][0]
            stop_name = first_result.get('stopPoint', {}).get('name', 'your stop')
            stop_name = stop_name.replace(', Göteborg', '').replace(', Goteborg', '')
            stop_name = normalize_swedish(stop_name)

        # Build simple response
        parts = []

        if 'results' in data and data['results']:
            for dep in data['results'][:5]:
                line_info = dep.get('serviceJourney', {}).get('line', {})
                line = line_info.get('shortName', 'unknown')
                direction = dep.get('serviceJourney', {}).get('direction', 'unknown')
                direction = normalize_swedish(direction)
                transport_mode = line_info.get('transportMode', 'bus')

                estimated_time_str = dep.get('estimatedTime', '')
                relative_time, _ = format_time(estimated_time_str) if estimated_time_str else ('-', '-')

                track = dep.get('stopPoint', {}).get('platform', '')

                vehicle = "Tram" if transport_mode == "tram" else "Bus"

                # Simple format: "Tram 3 to Destination in 5 min at platform A"
                parts.append(f"{vehicle} {line} to {direction} in {relative_time} at platform {track}")

            return f"From {stop_name}. " + ". ".join(parts) + "."
        else:
            return f"No departures from {stop_name}."

    except Exception as e:
        return f'Error: {str(e)}', 500


@app.route('/api/departures')
def get_departures():
    """API endpoint to get current departures as JSON."""
    stop_id = os.getenv('STOP_ID')

    if not stop_id:
        return jsonify({'error': 'STOP_ID not configured'}), 400

    try:
        api = VasttrafikAPI()
        data = api.get_departures(stop_id, limit=10)

        # Get stop name from the first result
        stop_name = "Your Stop"
        if 'results' in data and len(data['results']) > 0:
            first_result = data['results'][0]
            stop_name = first_result.get('stopPoint', {}).get('name', 'Your Stop')
            # Clean up the stop name (remove ", Göteborg" suffix)
            stop_name = stop_name.replace(', Göteborg', '').replace(', Goteborg', '')

        departures = []
        if 'results' in data and data['results']:
            for dep in data['results']:
                line_info = dep.get('serviceJourney', {}).get('line', {})
                line = line_info.get('shortName', 'N/A')
                direction = dep.get('serviceJourney', {}).get('direction', 'Unknown')

                # Get line colors from API
                bg_color = line_info.get('backgroundColor', '#0098db')
                fg_color = line_info.get('foregroundColor', '#ffffff')
                border_color = line_info.get('borderColor', '#ffffff')

                # Get transport mode (bus, tram, etc.)
                transport_mode = line_info.get('transportMode', 'bus')

                # Get planned and estimated times
                planned_time_str = dep.get('plannedTime', '')
                estimated_time_str = dep.get('estimatedTime', '')

                # Use estimated if available, otherwise planned
                departure_time = estimated_time_str or planned_time_str
                relative_time, actual_time = format_time(departure_time)

                # Get scheduled time separately
                _, scheduled_time = format_time(planned_time_str) if planned_time_str else ('-', '-')

                # Check if delayed or cancelled
                is_cancelled = dep.get('isCancelled', False)
                is_delayed = estimated_time_str and estimated_time_str != planned_time_str

                if is_cancelled:
                    relative_time = "CANCELLED"
                    status = "cancelled"
                elif is_delayed:
                    status = "delayed"
                else:
                    status = "on-time"

                track = dep.get('stopPoint', {}).get('platform', '-')

                departures.append({
                    'line': line,
                    'direction': direction,
                    'relative_time': relative_time,
                    'scheduled_time': scheduled_time,
                    'actual_time': actual_time,
                    'track': track,
                    'status': status,
                    'bg_color': bg_color,
                    'fg_color': fg_color,
                    'border_color': border_color,
                    'transport_mode': transport_mode
                })

        # Use Swedish timezone for updated timestamp
        sweden_tz = ZoneInfo('Europe/Stockholm')
        current_time = datetime.now(sweden_tz)

        return jsonify({
            'departures': departures,
            'stop_name': stop_name,
            'current_time': current_time.strftime('%H:%M'),
            'updated': current_time.strftime('%H:%M:%S')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Get port from environment or default to 8080
    port = int(os.getenv('PORT', 8080))

    # Run the server
    # Use 0.0.0.0 to make it accessible from other devices on your network
    print(f"Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
