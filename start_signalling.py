"""
Deep-Space Orbital Navigation and Signalling System — Server Entrypoint
=======================================================================
Mission Control command-line starter to deploy the standalone WebSocket
Signalling Beacon for interstellar peer discovery and room coordination.

Usage:
    python start_signalling.py [--host 127.0.0.1] [--port 8765]

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import sys
import argparse
import asyncio
import logging
from signalling import SignallingServer, cosmo_polo_telemetry


def parse_arguments():
    """Parses orbital launch parameters."""
    parser = argparse.ArgumentParser(
        description="Mission Control Orbital Signalling Server for TatHack 2026 Blockchain Simulation"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen for WebSocket beacons (default: 8765)")
    parser.add_argument("--heartbeat-timeout", type=float, default=30.0, help="Heartbeat timeout in seconds (default: 30.0)")
    parser.add_argument("--check-interval", type=float, default=2.0, help="Radar check interval in seconds (default: 2.0)")
    return parser.parse_args()


async def main():
    args = parse_arguments()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 70)
    print("🛰️  MISSION CONTROL — DEEP-SPACE SIGNALLING STATION DEPLOYMENT")
    print(f"📡 Status: {cosmo_polo_telemetry()}")
    print(f"🌌 Grid Coordinates: ws://{args.host}:{args.port}")
    print(f"⏱️  Heartbeat Timeout: {args.heartbeat_timeout}s | Radar Interval: {args.check_interval}s")
    print("=" * 70)

    server = SignallingServer(
        host=args.host,
        port=args.port,
        heartbeat_timeout=args.heartbeat_timeout,
        heartbeat_check_interval=args.check_interval,
    )
    await server.start()

    try:
        # Keep station operational until interrupt signal
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[!] Powering down orbital signalling station...")
    finally:
        await server.stop()
        print("[✓] Orbital beacon deactivated safely.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
        sys.exit(0)
