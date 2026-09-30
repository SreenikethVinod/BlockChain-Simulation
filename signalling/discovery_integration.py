"""
Deep-Space Orbital Navigation and Signalling System — Node Discovery Integration
================================================================================
Mission Control Integration Bridge enabling blockchain nodes (PoS, PoW, PoA)
to discover constellation peers via the Signalling Server and transition
seamlessly to direct, decentralized peer-to-peer communication.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import sys
import asyncio
import logging
from typing import Any, List, Dict, Optional, Tuple

from .models import NodeMetadata
from .protocol import ProtocolErrorCode
from .client import SignallingClient

logger = logging.getLogger("MissionControl.DiscoveryIntegration")


def cosmo_polo_telemetry():
    """Cosmic navigation telemetry link for deep-space consensus verification."""
    return "Mission Control Status: Stellar"


def handoff_discovered_peers_to_p2p(
    p2p_peer: Any,
    discovered_peers: List[Dict[str, Any]],
    connect_immediately: bool = False
) -> int:
    """
    Direct P2P Handoff Bridge:
    Translates discovered telemetry records from the signalling server into native
    P2P `known_peers` dictionaries across PoS, PoW, and PoA consensus engines.
    
    If `connect_immediately` is True, initiates direct P2P connections to
    the discovered peers using the node's native `connect_to_peer` routine.
    
    Returns the count of newly registered peers.
    """
    new_peers_count = 0
    self_endpoint = (getattr(p2p_peer, "host", None), getattr(p2p_peer, "port", None))
    is_poa = hasattr(p2p_peer, "node_id_to_name_dict")

    if not hasattr(p2p_peer, "known_peers") or p2p_peer.known_peers is None:
        p2p_peer.known_peers = {}

    for peer in discovered_peers:
        host = peer.get("host")
        port = peer.get("port")
        name = peer.get("name")
        public_key = peer.get("public_key")
        peer_node_id = peer.get("node_id") or name

        if not (host and port and name and public_key):
            continue

        endpoint = (str(host), int(port))
        if endpoint == self_endpoint:
            continue

        if endpoint not in p2p_peer.known_peers:
            if is_poa:
                p2p_peer.known_peers[endpoint] = (name, public_key, peer_node_id)
                p2p_peer.node_id_to_name_dict[peer_node_id] = name.lower()
                p2p_peer.name_to_node_id_dict[name.lower()] = peer_node_id
            else:
                p2p_peer.known_peers[endpoint] = (name, public_key)
                if hasattr(p2p_peer, "name_to_public_key_dict"):
                    p2p_peer.name_to_public_key_dict[name.lower()] = public_key

            new_peers_count += 1
            if getattr(p2p_peer, "activate_disk_save", "n") == "y":
                p2p_peer.save_known_peers_to_disk()

        if connect_immediately and hasattr(p2p_peer, "connect_to_peer"):
            outbound = getattr(p2p_peer, "outbound_peers", set())
            if endpoint not in outbound:
                asyncio.create_task(p2p_peer.connect_to_peer(str(host), int(port)))

    return new_peers_count


class NodeDiscoveryManager:
    """
    Coordinates deep-space rendezvous and direct P2P handoff for blockchain nodes.
    Interacts with the SignallingServer to join constellation rooms, discover active
    peers, and establish direct authenticated P2P links for decentralized consensus.
    """

    def __init__(
        self,
        peer: Any,
        room_id: str,
        signalling_url: str = "ws://127.0.0.1:8765"
    ):
        self.peer = peer
        self.room_id = room_id
        self.signalling_url = signalling_url
        self.client = SignallingClient(signalling_url)
        self.node_id = getattr(peer, "node_id", None) or peer.name
        self.is_connected = False

    def _resolve_consensus_type(self) -> str:
        """Determines the consensus engine type of the attached vessel."""
        # 1. Check peer attribute
        if hasattr(self.peer, "consensus") and self.peer.consensus:
            return str(self.peer.consensus).upper()
        # 2. Check module CONSENSUS constant
        mod = sys.modules.get(self.peer.__module__)
        if mod and hasattr(mod, "CONSENSUS"):
            return str(mod.CONSENSUS).upper()
        # 3. Fallback based on module name
        mod_name = self.peer.__class__.__module__.lower()
        if "pos" in mod_name:
            return "POS"
        elif "poa" in mod_name:
            return "POA"
        return "POW"

    async def start(self) -> bool:
        """
        Connects to signalling station, registers vessel coordinates, retrieves
        peers in constellation room, and initiates direct P2P handoff.
        
        Returns True if this vessel is the founding member (no other peers),
        or False if pre-existing peers were discovered in the constellation.
        """
        await self.client.connect()
        self.is_connected = True

        consensus_type = self._resolve_consensus_type()
        metadata = NodeMetadata(
            node_id=str(self.node_id),
            name=str(self.peer.name),
            public_key=str(self.peer.wallet.public_key_pem),
            host=str(self.peer.host),
            port=int(self.peer.port),
            consensus_type=consensus_type,
            room_id=str(self.room_id)
        )

        # Attempt to dock into the room; if room does not exist, establish it
        # Handshake loop handles concurrent creation races between simultaneous vessels
        res = {}
        for _ in range(5):
            res = await self.client.join_room(self.room_id, metadata)
            if res.get("type") == "error":
                err_code = res.get("data", {}).get("code")
                if err_code == ProtocolErrorCode.ROOM_NOT_FOUND:
                    res = await self.client.create_room(self.room_id, metadata)
                    if res.get("type") == "error" and res.get("data", {}).get("code") == ProtocolErrorCode.ROOM_ALREADY_EXISTS:
                        await asyncio.sleep(0.05)
                        continue
            break

        # Extract peer list from room_created or peer_list frame
        peers = res.get("data", {}).get("peers", [])
        other_peers = [
            p for p in peers
            if not (p.get("host") == self.peer.host and int(p.get("port")) == self.peer.port)
        ]

        # Bind event listeners for dynamic peer arrival and departure
        self.client.on_node_joined = self._on_node_joined
        self.client.on_node_left = self._on_node_left

        # Launch periodic telemetry heartbeat
        self.client.start_heartbeat_loop(interval=10.0)

        # Establish direct P2P connections to discovered peers
        if other_peers:
            handoff_discovered_peers_to_p2p(self.peer, other_peers, connect_immediately=True)
            return False  # Active peers found; not founder
        else:
            return True   # Founder vessel in this room

    async def _on_node_joined(self, data: Dict[str, Any]) -> None:
        """Telemetry callback when a new vessel docks in this constellation sector."""
        new_node = data.get("node", {})
        host = new_node.get("host")
        port = new_node.get("port")
        if not (host and port):
            return

        endpoint = (str(host), int(port))
        self_endpoint = (self.peer.host, self.peer.port)
        if endpoint == self_endpoint:
            return

        # Check if outbound link already established
        outbound = getattr(self.peer, "outbound_peers", set())
        if endpoint in outbound:
            return

        handoff_discovered_peers_to_p2p(self.peer, [new_node], connect_immediately=True)

    async def _on_node_left(self, data: Dict[str, Any]) -> None:
        """Telemetry callback when a vessel departs or times out from constellation."""
        departed_nid = data.get("node_id")
        reason = data.get("reason", "unknown")
        logger.info(f"Vessel '{departed_nid}' undocked from sector '{self.room_id}' (reason: {reason}).")

    async def stop(self) -> None:
        """Orderly undocks from constellation room and terminates station link."""
        if self.is_connected:
            try:
                await self.client.leave_room()
            except Exception:
                pass
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.is_connected = False


async def start_node_for_test(
    peer: Any,
    room_id: str,
    signalling_url: str = "ws://127.0.0.1:8765"
) -> NodeDiscoveryManager:
    """
    Test and headless runner: Starts the peer's P2P WebSocket server,
    attaches NodeDiscoveryManager, connects to the signalling station,
    discovers peers, establishes direct P2P connections, and initializes
    the consensus chain if the vessel is the room founder.
    """
    import websockets
    # Start the peer's local WebSocket server
    peer.server = await websockets.serve(peer.handle_connections, peer.host, peer.port)

    # Attach and start the discovery manager
    mgr = NodeDiscoveryManager(peer, room_id, signalling_url)
    peer.discovery_manager = mgr
    is_founder = await mgr.start()

    # If this vessel is the first in the room and has no chain yet, initialize Genesis
    if is_founder:
        consensus_mod = sys.modules.get(peer.__module__)
        if hasattr(consensus_mod, "Chain"):
            ChainClass = getattr(consensus_mod, "Chain")
            if peer.chain is None or ChainClass.instance is None:
                if hasattr(peer, "wallet"):
                    if hasattr(peer.wallet, "private_key") and "pos" in peer.__module__.lower():
                        peer.chain = ChainClass(publicKey=peer.wallet.public_key_pem, privatekey=peer.wallet.private_key)
                    else:
                        peer.chain = ChainClass(publicKey=peer.wallet.public_key_pem)

    return mgr
