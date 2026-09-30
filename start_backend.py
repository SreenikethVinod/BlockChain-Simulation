"""
Deep-Space Mission Control — Backend API Server Launcher
========================================================
CLI Launcher starting the FastAPI backend API server with uvicorn.

Usage:
    python start_backend.py --port 8000
    python start_backend.py --host 0.0.0.0 --port 8000 --consensus pos

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import sys
import argparse
import uvicorn
from backend.app import create_app, cosmo_polo_telemetry


def parse_args():
    parser = argparse.ArgumentParser(description="Start the Deep-Space Blockchain Mission Control API.")
    parser.add_argument("--host", default="127.0.0.1", help="API host binding address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="API HTTP port (default: 8000)")
    parser.add_argument("--consensus", default="pos", choices=["pos", "pow", "poa"], help="Consensus engine [pos/pow/poa]")
    parser.add_argument("--node-port", type=int, default=5000, help="Local node P2P port (default: 5000)")
    parser.add_argument("--room", default=None, help="Constellation room ID to connect to live simulation (e.g. TATHACK-DEMO)")
    parser.add_argument("--signalling-url", default="ws://127.0.0.1:8765", help="Signalling server WebSocket URL for peer discovery")
    parser.add_argument("--node-name", default="mission_control", help="Observer node name (default: mission_control)")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload for development")
    return parser.parse_args()


def main():
    args = parse_args()
    print("=" * 70)
    print("🛰️ MISSION CONTROL — BLOCKCHAIN SIMULATION BACKEND API")
    print(f"📡 Status: {cosmo_polo_telemetry()}")
    print(f"🌐 Binding API on http://{args.host}:{args.port}")
    print(f"📚 OpenAPI Interactive Docs: http://{args.host}:{args.port}/api/docs")
    if args.room:
        print(f"🌌 Connecting to Live Constellation Room: {args.room} via {args.signalling_url}")
    else:
        print(f"🔭 Mode: Standalone / In-Memory Observation Mode")
    print("=" * 70)

    peer = None
    if args.room:
        if args.consensus == "pos":
            from consensus.pos.p2p import Peer as PoSPeer
            peer = PoSPeer(args.host, args.node_port, args.node_name, True, "n", "n", node_id=args.node_name)
        elif args.consensus == "pow":
            from consensus.pow.p2p import Peer as PoWPeer
            peer = PoWPeer(args.host, args.node_port, args.node_name, False, "n", "n", node_id=args.node_name)
        elif args.consensus == "poa":
            from consensus.poa.p2p import Peer as PoAPeer
            peer = PoAPeer(args.host, args.node_port, args.node_name, "n", "n", node_id=args.node_name)

        import threading, asyncio
        def run_peer():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(peer.start(room_id=args.room, signalling_url=args.signalling_url))
            except (asyncio.CancelledError, KeyboardInterrupt):
                pass
            except Exception as e:
                print(f"[Observer Peer] Offline or closed: {e}")

        t = threading.Thread(target=run_peer, daemon=True)
        t.start()

    app_instance = create_app(peer=peer)
    uvicorn.run(app_instance, host=args.host, port=args.port, reload=args.reload)



if __name__ == "__main__":
    main()
