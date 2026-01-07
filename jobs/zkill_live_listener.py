#!/usr/bin/env python3
"""
zKillboard Live Listener - Background Worker

Continuously pulls killmails from zKillboard RedisQ and processes them
in real-time for combat intelligence and hotspot detection.

This should run as a long-running background process (systemd service or screen).

Usage:
    python3 -m jobs.zkill_live_listener                    # Start listener
    python3 -m jobs.zkill_live_listener --verbose          # Verbose output
"""

import sys
import os
import asyncio
import argparse
import signal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.zkillboard_live_service import zkill_live_service


# Signal handling for graceful shutdown
def signal_handler(signum, frame):
    print("\nShutdown signal received. Stopping listener...")
    zkill_live_service.stop()
    sys.exit(0)


async def main():
    parser = argparse.ArgumentParser(
        description='zKillboard Live Listener - Real-time killmail processing'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start listening
    print("=" * 60)
    print("zKillboard Live Listener - EVE Co-Pilot")
    print("=" * 60)
    print("Status: Starting...")
    print(f"Redis: {zkill_live_service.redis_client.ping()}")
    print(f"Hotspot threshold: {5} kills in 5 minutes")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    try:
        await zkill_live_service.listen_zkillboard(verbose=args.verbose)
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
