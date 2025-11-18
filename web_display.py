#!/usr/bin/env python3
"""
Västtrafik Departures Web Display
A web interface optimized for TV viewing.
"""

import os
from flask import Flask, render_template, jsonify
from datetime import datetime
from vasttrafik_api import VasttrafikAPI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


def format_time(departure_time_str):
    """Format departure time - returns tuple of (relative_time, actual_time)."""
    try:
        # Remove timezone offset and milliseconds for parsing
        time_str = departure_time_str.split('.')[0]
        if '+' in departure_time_str:
            time_str = departure_time_str.split('+')[0].split('.')[0]

        dept_time = datetime.fromisoformat(time_str)
        now = datetime.now()
        diff = (dept_time - now).total_seconds() / 60

        # Get the actual time HH:MM
        actual_time = dept_time.strftime("%H:%M")

        if diff < 1:
            relative_time = "Now"
        elif diff < 60:
            relative_time = f"{int(diff)} min"
        else:
            relative_time = "-"

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


@app.route('/api/departures')
def get_departures():
    """API endpoint to get current departures as JSON."""
    stop_id = os.getenv('STOP_ID')

    if not stop_id:
        return jsonify({'error': 'STOP_ID not configured'}), 400

    try:
        api = VasttrafikAPI()
        data = api.get_departures(stop_id, limit=10)

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
                    'border_color': border_color
                })

        return jsonify({
            'departures': departures,
            'updated': datetime.now().strftime('%H:%M:%S')
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
