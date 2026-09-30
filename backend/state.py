"""
Deep-Space Mission Control — Simulation State & Node Bridge
===========================================================
Bridges the FastAPI REST and WebSocket layers to underlying blockchain nodes
(PoS, PoW, PoA). Extracts safe, sanitized telemetry without exposing secrets.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import time
import base64
from typing import Any, Optional, Dict, List
from .events import EventBroadcaster
from .models import (
    BlockSummary,
    BlockDetail,
    TransactionSummary,
    PoSBlockMetadata,
)


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


class SimulationBackendState:
    """
    Central operational bridge connecting FastAPI to blockchain node simulation.
    Handles peer inspection, chain extraction, attack monitoring, and event dispatch.
    """

    def __init__(self, peer: Optional[Any] = None):
        self.peer = peer
        self.is_standalone = (peer is None)
        self.broadcaster = EventBroadcaster()
        self.attack_telemetry = {
            "forks_detected": 0,
            "slashing_incidents": 0,
            "invalid_blocks_rejected": 0,
            "double_sign_attempts": 0,
            "malicious_peers_detected": [],
            "incidents": [],
        }
        from .metrics import BlockchainMetricsCollector
        self.metrics = BlockchainMetricsCollector(self)

    def set_peer(self, peer: Any, is_standalone: bool = False) -> None:
        """Attaches an active blockchain node vessel to the backend bridge."""
        self.peer = peer
        self.is_standalone = is_standalone or getattr(peer, "is_observation", False)

    def get_peer(self) -> Any:
        """
        Returns the active peer instance.
        If none is attached, automatically initializes an in-memory observation node.
        """
        if self.peer is not None:
            return self.peer

        self.is_standalone = True

        # Check if a chain singleton is active in memory
        from consensus.pos.blockchain_structures import Chain as PoSChain
        from consensus.pos.p2p import Peer as PoSPeer

        # Initialize observation node with disk disabled
        obs_node = PoSPeer(
            host="127.0.0.1",
            port=5000,
            name="mission_control_node",
            staker=True,
            activate_disk_load="n",
            activate_disk_save="n",
            node_id="mission_control_node"
        )
        if obs_node.chain is None or PoSChain.instance is None:
            obs_node.chain = PoSChain(
                publicKey=obs_node.wallet.public_key_pem,
                privatekey=obs_node.wallet.private_key
            )
        self.peer = obs_node
        return self.peer

    def get_consensus_type(self) -> str:
        """Resolves the active consensus engine identifier."""
        peer = self.get_peer()
        if hasattr(peer, "consensus") and peer.consensus:
            return str(peer.consensus).lower()
        mod_name = peer.__class__.__module__.lower()
        if "pos" in mod_name:
            return "pos"
        elif "poa" in mod_name:
            return "poa"
        return "pow"

    def get_chain(self) -> Optional[Any]:
        """Retrieves the active blockchain instance."""
        peer = self.get_peer()
        if hasattr(peer, "chain") and peer.chain is not None:
            return peer.chain

        # Check PoS singleton
        from consensus.pos.blockchain_structures import Chain as PoSChain
        if PoSChain.instance is not None:
            return PoSChain.instance

        # Check PoW singleton
        from consensus.pow.blockchain_structures import Chain as PoWChain
        if PoWChain.instance is not None:
            return PoWChain.instance

        # Check PoA singleton
        from consensus.poa.blockchain_structures import Chain as PoAChain
        if PoAChain.instance is not None:
            return PoAChain.instance

        return None

    def get_blocks(self) -> List[Any]:
        """Returns the list of confirmed blocks in the canonical chain."""
        chain = self.get_chain()
        if chain and hasattr(chain, "chain"):
            return chain.chain
        return []

    def calc_balance(self, public_key: str) -> float:
        """Calculates current balance for a public key safely."""
        chain = self.get_chain()
        peer = self.get_peer()
        if not chain or not hasattr(chain, "calc_balance"):
            return 0.0

        try:
            mem_pool = getattr(peer, "mem_pool", [])
            current_stakes = list(getattr(peer, "current_stakes", []))
            return float(chain.calc_balance(public_key, mem_pool, current_stakes))
        except Exception as e1:
            print("Error in calc_balance (first attempt):", repr(e1))
            try:
                return float(chain.calc_balance(public_key))
            except Exception as e:
                print("Error in calc_balance:", repr(e))
                return 0.0

    def extract_safe_block_summary(self, block: Any, height: int) -> BlockSummary:
        """Extracts sanitized, non-secret summary of a block."""
        consensus_type = self.get_consensus_type()

        # Resolve block creator
        creator = (
            getattr(block, "creator", None) or
            getattr(block, "miner", None) or
            getattr(block, "miner_node_id", None) or
            getattr(block, "miner_public_key", None) or
            "Unknown"
        )

        # Resolve transactions count
        txs = getattr(block, "transactions", []) or []
        tx_count = len(txs)

        # Hash resolution: Block.hash is a @property returning a str — access directly.
        block_hash = getattr(block, "hash", None)
        if not block_hash:
            block_hash = "GENESIS_HASH" if height == 0 else "UNKNOWN_HASH"


        # PoS metadata
        pos_meta = None
        if consensus_type == "pos":
            vrf_b64 = None
            raw_vrf = getattr(block, "vrf_proof", None)
            if raw_vrf:
                vrf_b64 = base64.b64encode(raw_vrf).decode() if isinstance(raw_vrf, bytes) else str(raw_vrf)

            stakers_list = []
            for s in getattr(block, "stakers", []):
                stakers_list.append({
                    "staker": getattr(s, "staker", str(s)),
                    "amt": getattr(s, "amt", 0)
                })

            pos_meta = PoSBlockMetadata(
                seed=getattr(block, "seed", None),
                vrf_proof_b64=vrf_b64,
                staked_amt=getattr(block, "staked_amt", 0),
                stakers_count=len(stakers_list),
                stakers=stakers_list,
                slash_creator=getattr(block, "slash_creator", False)
            )

        return BlockSummary(
            height=height,
            hash=str(block_hash),
            previous_hash=getattr(block, "prevHash", None),
            creator=str(creator),
            timestamp=getattr(block, "ts", None),
            transaction_count=tx_count,
            consensus_type=consensus_type,
            pos_metadata=pos_meta
        )

    def extract_safe_block_detail(self, block: Any, height: int) -> BlockDetail:
        """Extracts detailed sanitized block object with transaction list."""
        summary = self.extract_safe_block_summary(block, height)

        tx_summaries: List[TransactionSummary] = []
        for tx in getattr(block, "transactions", []):
            sign_b64 = None
            raw_sign = getattr(tx, "sign", None)
            if raw_sign:
                sign_b64 = base64.b64encode(raw_sign).decode() if isinstance(raw_sign, bytes) else str(raw_sign)

            tx_summaries.append(TransactionSummary(
                id=str(getattr(tx, "id", "")),
                sender=str(getattr(tx, "sender", "")),
                receiver=str(getattr(tx, "receiver", "")),
                payload=getattr(tx, "payload", None),
                timestamp=getattr(tx, "ts", None),
                sign=sign_b64
            ))

        return BlockDetail(
            height=height,
            id=str(getattr(block, "id", "")),
            hash=summary.hash,
            previous_hash=summary.previous_hash,
            creator=summary.creator,
            timestamp=summary.timestamp,
            transactions=tx_summaries,
            transaction_count=len(tx_summaries),
            consensus_type=summary.consensus_type,
            pos_metadata=summary.pos_metadata,
            files=getattr(block, "files", None)
        )

    # ==========================================================================
    # Attack & Incident Recording
    # ==========================================================================

    def record_fork(self, height: int, old_hash: str, new_hash: str, reason: str = "") -> None:
        """Records a chain re-organization / fork detection incident."""
        self.attack_telemetry["forks_detected"] += 1
        incident = {
            "type": "fork_detected",
            "time": time.time(),
            "height": height,
            "old_hash": old_hash,
            "new_hash": new_hash,
            "reason": reason
        }
        self.attack_telemetry["incidents"].append(incident)
        if len(self.attack_telemetry["incidents"]) > 100:
            self.attack_telemetry["incidents"].pop(0)
        if hasattr(self, "metrics") and self.metrics:
            self.metrics.record_fork(height, old_hash, new_hash)

    def record_slashing(self, validator: str, reason: str, height: Optional[int] = None) -> None:
        """Records a validator slashing occurrence."""
        self.attack_telemetry["slashing_incidents"] += 1
        incident = {
            "type": "validator_slashed",
            "time": time.time(),
            "validator": validator,
            "reason": reason,
            "height": height
        }
        self.attack_telemetry["incidents"].append(incident)
        if len(self.attack_telemetry["incidents"]) > 100:
            self.attack_telemetry["incidents"].pop(0)
        if hasattr(self, "metrics") and self.metrics:
            self.metrics.record_slashing(validator, reason)

    def record_double_sign(self, validator: str, b1_id: str, b2_id: str) -> None:
        """Records a double-signing attempt detection."""
        self.attack_telemetry["double_sign_attempts"] += 1
        self.attack_telemetry["slashing_incidents"] += 1
        incident = {
            "type": "double_sign_attempt",
            "time": time.time(),
            "validator": validator,
            "block1": b1_id,
            "block2": b2_id
        }
        self.attack_telemetry["incidents"].append(incident)
        if len(self.attack_telemetry["incidents"]) > 100:
            self.attack_telemetry["incidents"].pop(0)


# Global singleton instance
_backend_state = SimulationBackendState()


def get_backend_state() -> SimulationBackendState:
    """Accesses the Mission Control backend state singleton."""
    return _backend_state


def set_active_peer(peer: Any, is_standalone: bool = False) -> None:
    """Configures the active blockchain node vessel in the backend bridge."""
    _backend_state.set_peer(peer, is_standalone=is_standalone)
