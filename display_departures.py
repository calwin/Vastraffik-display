#!/usr/bin/env python3
"""
Västtrafik Departures Display
Displays real-time departures for your stop.
"""

import os
import sys
import requests
from datetime import datetime
from vasttrafik_api import VasttrafikAPI
from dotenv import load_dotenv

load_dotenv()


def format_time(departure_time_str):
    """Format departure time as relative or absolute time."""
    try:
        # Remove timezone offset and milliseconds for parsing
        time_str = departure_time_str.split('.')[0]
        if '+' in departure_time_str:
            time_str = departure_time_str.split('+')[0].split('.')[0]

        dept_time = datetime.fromisoformat(time_str)
        now = datetime.now()
        diff = (dept_time - now).total_seconds() / 60

        if diff < 1:
            return "Now"
        elif diff < 60:
            return f"{int(diff)} min"
        else:
            return dept_time.strftime("%H:%M")
    except Exception as e:
        # If parsing fails, try to extract HH:MM from the string
        if 'T' in departure_time_str:
            try:
                return departure_time_str.split('T')[1][:5]
            except:
                pass
        return departure_time_str


def display_departures(stop_id, limit=15):
    """Display departures for the given stop."""
    api = VasttrafikAPI()

    try:
        data = api.get_departures(stop_id, limit=limit)

        print("\n" + "="*80)
        print(f"DEPARTURES - {datetime.now().strftime('%H:%M:%S')}")
        print("="*80)
        print(f"{'Line':<8} {'Direction':<35} {'Departure':<12} {'Track':<8}")
        print("-"*80)

        if 'results' in data and data['results']:
            for dep in data['results']:
                line = dep.get('serviceJourney', {}).get('line', {}).get('shortName', 'N/A')
                direction = dep.get('serviceJourney', {}).get('direction', 'Unknown')

                # Get planned or estimated time
                departure_time = dep.get('estimatedTime') or dep.get('plannedTime', '')
                time_str = format_time(departure_time)

                # Check if delayed
                is_cancelled = dep.get('isCancelled', False)
                is_delayed = dep.get('estimatedTime') and dep.get('estimatedTime') != dep.get('plannedTime')

                if is_cancelled:
                    time_str = "CANCELLED"
                elif is_delayed:
                    time_str += " (delayed)"

                track = dep.get('stopPoint', {}).get('platform', '-')

                # Truncate direction if too long
                if len(direction) > 34:
                    direction = direction[:31] + "..."

                print(f"{line:<8} {direction:<35} {time_str:<12} {track:<8}")
        else:
            print("No departures found.")

        print("="*80 + "\n")

    except requests.exceptions.HTTPError as e:
        print(f"API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def search_stops(query):
    """Search for stops by name."""
    api = VasttrafikAPI()

    try:
        results = api.search_stop(query)

        print(f"\nSearch results for '{query}':")
        print("-"*80)

        if 'results' in results and results['results']:
            for i, location in enumerate(results['results'], 1):
                name = location.get('name', 'Unknown')
                gid = location.get('gid', 'N/A')
                print(f"{i}. {name}")
                print(f"   GID: {gid}")
                print()
        else:
            print("No stops found.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Västtrafik Departures Display')
    parser.add_argument('--search', type=str, help='Search for a stop by name')
    parser.add_argument('--stop-id', type=str, help='Stop ID to display departures for')
    parser.add_argument('--limit', type=int, default=15, help='Number of departures to show')

    args = parser.parse_args()

    if args.search:
        search_stops(args.search)
    elif args.stop_id:
        display_departures(args.stop_id, args.limit)
    else:
        # Use stop from .env if available
        stop_id = os.getenv('STOP_ID')
        if stop_id:
            display_departures(stop_id, args.limit)
        else:
            parser.print_help()
            print("\nPlease provide --search to find your stop, or --stop-id to show departures.")
