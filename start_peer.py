"""
Deep-Space Orbital Node Launcher — Decentralized Peer Starter
=============================================================
Launches a blockchain node (PoS, PoW, or PoA) with isolated storage,
connects to the orbital Signalling Server for room-based peer discovery,
and establishes direct P2P WebSocket connections for consensus.

Supports both interactive terminal prompts and command-line arguments.
Retains manual bootstrap as a backward-compatible fallback mode.

Usage:
    python start_peer.py --consensus pos --name node1 --port 5001 --room TATHACK-DEMO
    python start_peer.py  (Interactive mode)

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import sys
import argparse
import asyncio
import shutil
import os
from storage.storage_manager import get_consensus_dir
from consensus.poa.p2p import Peer as PoAPeer
from consensus.pos.p2p import Peer as PoSPeer
from consensus.pow.p2p import Peer as PoWPeer
from consensus.poa.mal_node import Peer as PoaMalPeer
from consensus.pos.mal_node import Peer as PosMalPeer
from consensus.pow.mal_node import Peer as PowMalPeer


def cosmo_polo_telemetry():
    """Cosmic navigation telemetry link for deep-space consensus verification."""
    return "Mission Control Status: Stellar"


def parse_args():
    """Parses command line arguments if provided."""
    parser = argparse.ArgumentParser(description="Launch a blockchain simulation node with room discovery.")
    parser.add_argument("--consensus", choices=["poa", "pos", "pow"], default=None, help="Consensus engine [poa/pos/pow]")
    parser.add_argument("--name", default=None, help="Node name and identity (e.g. node1, apollo)")
    parser.add_argument("--node-id", default=None, help="Explicit node ID for storage isolation (defaults to name)")
    parser.add_argument("--host", default="127.0.0.1", help="Local host binding address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Local P2P listening port (e.g. 5001)")
    parser.add_argument("--room", default=None, help="Constellation room ID for signalling discovery (e.g. TATHACK-DEMO)")
    parser.add_argument("--signalling-url", default="ws://127.0.0.1:8765", help="Signalling server WebSocket URL")
    parser.add_argument("--manual", action="store_true", help="Fallback to manual bootstrap mode instead of room discovery")
    parser.add_argument("--bootstrap-host", default=None, help="Bootstrap node host for manual mode")
    parser.add_argument("--bootstrap-port", type=int, default=None, help="Bootstrap node port for manual mode")
    parser.add_argument("--disk-load", choices=["y", "n"], default="n", help="Load saved state from disk (y/n)")
    parser.add_argument("--disk-save", choices=["y", "n"], default="y", help="Continuously backup state to disk (y/n)")
    parser.add_argument("--miner", action="store_true", default=True, help="Mine blocks (for PoW)")
    parser.add_argument("--staker", action="store_true", default=True, help="Stake coins (for PoS)")
    parser.add_argument("--malicious", action="store_true", default=False, help="Run as malicious adversarial node")
    parser.add_argument("--fresh", action="store_true", default=False, help="Wipe local storage and start a fresh demo state")
    return parser.parse_known_args()[0]


def start_peer():
    args = parse_args()

    # If any essential arguments were supplied via CLI, use non-interactive path
    interactive = (args.consensus is None and args.port is None and args.name is None)

    if interactive:
        print("=" * 70)
        print("🚀 MISSION CONTROL — DEEP-SPACE BLOCKCHAIN NODE LAUNCHER")
        print(f"📡 Status: {cosmo_polo_telemetry()}")
        print("=" * 70)

        # 1. Choose consensus type
        raw_consensus = input("Enter Consensus [poa/pos/pow] (default: pow): ").strip().lower()
        consensus = raw_consensus if raw_consensus in ["poa", "pos", "pow"] else "pow"

        # 2. Choose node name/ID
        raw_name = input("Enter Node Name/ID (default: node1): ").strip()
        name = raw_name if raw_name else "node1"
        node_id = name

        # 3. Choose local P2P port
        raw_host = input("Enter Host (default: 127.0.0.1): ").strip()
        host = raw_host if raw_host else "127.0.0.1"

        raw_port = input("Enter Local Port (default: 5001): ").strip()
        port = int(raw_port) if raw_port else 5001

        # 4. Choose discovery mode
        print("\nDiscovery Mode:")
        print("  [1] Room-Based Discovery via Signalling Station (Primary)")
        print("  [2] Manual Bootstrap (Legacy Fallback)")
        mode_choice = input("Enter choice [1/2] (default: 1): ").strip()

        if mode_choice == "2":
            action = input("Enter 'create' to create a network or 'connect' to join: ").strip().lower()
            room_id = None
            signalling_url = None
            bootstrap_host = None
            bootstrap_port = None
            if action == "connect":
                bootstrap_host = input("Enter bootstrap host to connect: ").strip()
                bootstrap_port = int(input("Enter bootstrap port to connect: ").strip())
        else:
            raw_room = input("Enter Constellation Room ID (default: TATHACK-DEMO): ").strip()
            room_id = raw_room if raw_room else "TATHACK-DEMO"
            raw_url = input("Enter Signalling Station URL (default: ws://127.0.0.1:8765): ").strip()
            signalling_url = raw_url if raw_url else "ws://127.0.0.1:8765"
            bootstrap_host = None
            bootstrap_port = None

        activate_disk_load = input("Load saved data from disk if available? (y/n, default: n): ").strip().lower() or "n"
        activate_disk_save = input("Backup data continuously to disk? (y/n, default: y): ").strip().lower() or "y"

        mal_raw = input("Run as malicious adversarial node? (y/n, default: n): ").strip().lower()
        mal = (mal_raw == "y")

        staker = True
        miner = True
        if consensus == "pos" and not mal:
            staker_raw = input("Participate as active validator/staker? (y/n, default: y): ").strip().lower()
            staker = (staker_raw != "n")
        elif consensus == "pow" and not mal:
            miner_raw = input("Participate as active miner? (y/n, default: y): ").strip().lower()
            miner = (miner_raw != "n")

    else:
        # CLI Flag Driven Path
        consensus = args.consensus or "pow"
        name = args.name or "node1"
        node_id = args.node_id or name
        host = args.host or "127.0.0.1"
        port = args.port or 5001
        activate_disk_load = args.disk_load
        activate_disk_save = args.disk_save
        mal = args.malicious
        staker = args.staker
        miner = args.miner

        if args.manual:
            room_id = None
            signalling_url = None
            bootstrap_host = args.bootstrap_host
            bootstrap_port = args.bootstrap_port
        else:
            room_id = args.room or "TATHACK-DEMO"
            signalling_url = args.signalling_url
            bootstrap_host = None
            bootstrap_port = None
        
        if args.fresh:
            # Wipe local storage for this node
            target_dir = get_consensus_dir(consensus, node_id)
            if os.path.exists(target_dir):
                print(f"[!] Wiping existing local storage at {target_dir}")
                shutil.rmtree(target_dir, ignore_errors=True)
            activate_disk_load = "n"

    print(f"\n[+] Deploying vessel '{name}' ({consensus.upper()}) on {host}:{port}")
    if room_id:
        print(f"[+] Rendezvous Room: {room_id} via {signalling_url}")
    elif bootstrap_host:
        print(f"[+] Manual Bootstrap: Connecting to {bootstrap_host}:{bootstrap_port}")
    else:
        print(f"[+] Manual Bootstrap: Standalone Genesis Node")

    # Instantiate peer with isolated storage directory
    peer = None
    if consensus == "poa":
        if not mal:
            peer = PoAPeer(host, port, name, activate_disk_load, activate_disk_save, node_id=node_id)
        else:
            peer = PoaMalPeer(host, port, name, activate_disk_load, activate_disk_save)
        peer.name_to_node_id_dict[peer.name.lower()] = peer.node_id
        peer.node_id_to_name_dict[peer.node_id] = peer.name.lower()

    elif consensus == "pos":
        if not mal:
            peer = PoSPeer(host, port, name, staker, activate_disk_load, activate_disk_save, node_id=node_id)
        else:
            peer = PosMalPeer(host, port, name, True, activate_disk_load, activate_disk_save)

    else:  # pow
        if not mal:
            peer = PoWPeer(host, port, name, miner, activate_disk_load, activate_disk_save, node_id=node_id)
        else:
            peer = PowMalPeer(host, port, name, True, activate_disk_load, activate_disk_save)

    try:
        asyncio.run(peer.start(
            bootstrap_host=bootstrap_host,
            bootstrap_port=bootstrap_port,
            room_id=room_id,
            signalling_url=signalling_url
        ))
    except KeyboardInterrupt:
        print("\nShutting Down...")


if __name__ == "__main__":
    start_peer()