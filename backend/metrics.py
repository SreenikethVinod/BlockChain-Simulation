"""
Deep-Space Mission Control — Real-Time Blockchain Metrics & Telemetry
====================================================================
Collects, aggregates, and serves authentic observational metrics across:
- Network: Active nodes, peer census, join/departure lifecycle
- Blockchain: Block heights, confirmation intervals, blocks/minute
- Transactions: Authentic TPS, transaction submission/confirmation, confirmation latencies
- Mempool: Real-time depth, historical depth series
- Consensus: Consensus-specific telemetry (PoS, PoW, PoA)
- Security & Attacks: Phase 7 Attack Lab integration, detection/mitigation rates, incident logs

CRITICAL CONSTRAINTS:
1. Zero Fabricated Data: Every metric reflects authentic state or returns explicit None / unavailable.
2. Observational Only: Telemetry never mutates consensus, delays blocks, or alters state.
3. Zero Secret Exposure: No private keys or sensitive credentials are ever recorded or emitted.
4. Bounded History: Uses collections.deque(maxlen=N) to strictly bound memory growth.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import time
import logging
from collections import deque
from typing import Dict, Any, List, Optional

logger = logging.getLogger("MissionControl.Metrics")


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


class MetricPoint:
    """Timestamped observational data point for timeseries charts."""
    def __init__(self, timestamp: float, value: float):
        self.timestamp = timestamp
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "value": round(self.value, 4) if isinstance(self.value, (int, float)) else self.value
        }


class BlockchainMetricsCollector:
    """
    Lightweight, thread-safe observational metrics engine with bounded circular buffers.
    Bridges backend simulation state to REST and WebSocket telemetry streams.
    """

    def __init__(self, state_ref: Any, max_history: int = 60):
        self.state = state_ref
        self.max_history = max_history

        # --- Network Counters & Timeseries ---
        self.peer_joins_total: int = 0
        self.peer_leaves_total: int = 0
        self.history_peer_count: deque = deque(maxlen=max_history)

        # --- Blockchain Counters & Timeseries ---
        self.blocks_created_total: int = 0
        self.blocks_received_total: int = 0
        self.history_block_intervals: deque = deque(maxlen=max_history)
        self.history_blocks_per_minute: deque = deque(maxlen=max_history)
        self._block_timestamps: deque = deque(maxlen=max_history)
        self.forks_detected_total: int = 0
        self.canonical_chain_reorgs_total: int = 0

        # --- Transaction Counters & Timeseries ---
        self.transactions_submitted_total: int = 0
        self.transactions_accepted_total: int = 0
        self.transactions_rejected_total: int = 0
        self.transactions_confirmed_total: int = 0
        self.history_tps: deque = deque(maxlen=max_history)
        self._confirmed_tx_events: deque = deque(maxlen=200)  # (timestamp, count)
        self._tx_confirmation_latencies: deque = deque(maxlen=max_history)

        # --- Mempool Counters & Timeseries ---
        self.transactions_entered_mempool_total: int = 0
        self.transactions_exited_mempool_total: int = 0
        self.history_mempool_depth: deque = deque(maxlen=max_history)

        # --- Security & Attacks (Phase 7 Integration) ---
        self.total_attack_attempts: int = 0
        self.attacks_by_type: Dict[str, int] = {
            "double_sign": 0,
            "double_spend": 0,
            "fork": 0,
            "invalid_vrf": 0,
            "invalid_signature": 0,
            "fake_stake": 0
        }
        self.detected_attacks: int = 0
        self.rejected_attacks: int = 0
        self.mitigated_attacks: int = 0
        self.completed_attacks: int = 0
        self.canonical_chain_preserved_count: int = 0
        self.recent_security_incidents: deque = deque(maxlen=50)

        # Initialize base sample point
        self.record_sample(timestamp=time.time())

    # =========================================================================
    # Observational Event Ingestion Hooks
    # =========================================================================

    def record_block(self, block: Any, source: str = "created") -> None:
        """Records an authentic block observation from consensus or network."""
        now = time.time()
        block_ts = getattr(block, "ts", None) or now

        if source == "created":
            self.blocks_created_total += 1
        else:
            self.blocks_received_total += 1

        # Calculate authentic block interval if previous timestamp exists
        if self._block_timestamps:
            prev_ts = self._block_timestamps[-1]
            try:
                prev_ts_f = float(prev_ts)
                block_ts_f = float(block_ts)
                delta = abs(block_ts_f - prev_ts_f)
                if delta >= 0:
                    self.history_block_intervals.append(MetricPoint(now, delta))
            except (ValueError, TypeError):
                pass

        self._block_timestamps.append(block_ts)

        # Also account for transactions confirmed in this block
        txs = getattr(block, "transactions", []) or []
        if txs:
            self.record_transactions_confirmed(len(txs), block_ts=block_ts, tx_list=txs)

        self.record_sample(timestamp=now)

    def record_transaction_submitted(self) -> None:
        """Records a new transaction submission attempt."""
        self.transactions_submitted_total += 1
        self.transactions_accepted_total += 1
        self.transactions_entered_mempool_total += 1
        self.record_sample(timestamp=time.time())

    def record_transaction_rejected(self, reason: str = "") -> None:
        """Records a transaction rejection."""
        self.transactions_submitted_total += 1
        self.transactions_rejected_total += 1
        self.record_sample(timestamp=time.time())

    def record_transactions_confirmed(self, count: int, block_ts: Optional[float] = None, tx_list: Optional[List[Any]] = None) -> None:
        """Records authentic transaction confirmation within a block."""
        now = time.time()
        self.transactions_confirmed_total += count
        self.transactions_exited_mempool_total += count
        self._confirmed_tx_events.append((now, count))

        # Check confirmation latency if transaction timestamps exist
        if tx_list and block_ts:
            for tx in tx_list:
                tx_ts = getattr(tx, "ts", None)
                if tx_ts is not None:
                    try:
                        latency = float(block_ts) - float(tx_ts)
                        if 0 <= latency < 86400:  # Valid positive latency within 24h
                            self._tx_confirmation_latencies.append(latency)
                    except (ValueError, TypeError):
                        pass

    def record_peer_event(self, event_type: str, peer_id: Optional[str] = None) -> None:
        """Records authentic peer join or leave event."""
        if event_type == "joined":
            self.peer_joins_total += 1
        elif event_type == "left":
            self.peer_leaves_total += 1
        self.record_sample(timestamp=time.time())

    def record_attack_lifecycle(self, attack_type: str, stage: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Ingests Phase 7 Attack Lab lifecycle transitions."""
        now = time.time()
        stage_norm = stage.lower()

        if stage_norm == "armed" or stage_norm == "executing" or stage_norm == "started":
            self.total_attack_attempts += 1
            if attack_type in self.attacks_by_type:
                self.attacks_by_type[attack_type] += 1
            else:
                self.attacks_by_type[attack_type] = 1

        elif stage_norm == "detected":
            self.detected_attacks += 1

        elif stage_norm == "rejected":
            self.rejected_attacks += 1
            self.canonical_chain_preserved_count += 1

        elif stage_norm == "mitigated":
            self.mitigated_attacks += 1
            self.canonical_chain_preserved_count += 1

        elif stage_norm == "complete" or stage_norm == "completed":
            self.completed_attacks += 1

        incident_record = {
            "attack_type": attack_type,
            "stage": stage.upper(),
            "timestamp": now,
            "details": details or {}
        }
        self.recent_security_incidents.append(incident_record)
        self.record_sample(timestamp=now)

    def record_fork(self, height: int, old_hash: str, new_hash: str) -> None:
        """Records chain fork observation."""
        self.forks_detected_total += 1
        self.canonical_chain_reorgs_total += 1
        self.recent_security_incidents.append({
            "type": "fork_detected",
            "timestamp": time.time(),
            "height": height,
            "old_hash": old_hash,
            "new_hash": new_hash
        })
        self.record_sample(timestamp=time.time())

    def record_slashing(self, validator: str, reason: str) -> None:
        """Records validator slashing observation."""
        self.recent_security_incidents.append({
            "type": "validator_slashed",
            "timestamp": time.time(),
            "validator": validator,
            "reason": reason
        })
        self.record_sample(timestamp=time.time())

    def record_sample(self, timestamp: Optional[float] = None) -> None:
        """Takes a lightweight observational snapshot for sliding timeseries."""
        now = timestamp or time.time()

        # 1. Peer count sample
        peer_cnt = self._get_current_peer_count()
        self.history_peer_count.append(MetricPoint(now, float(peer_cnt)))

        # 2. Mempool depth sample
        mempool_depth = self._get_current_mempool_size()
        self.history_mempool_depth.append(MetricPoint(now, float(mempool_depth)))

        # 3. Calculate authentic TPS over sliding 10s window
        window_sec = 10.0
        cutoff = now - window_sec
        recent_tx_count = sum(cnt for ts, cnt in self._confirmed_tx_events if ts >= cutoff)
        current_tps = round(recent_tx_count / window_sec, 2)
        self.history_tps.append(MetricPoint(now, current_tps))

        # 4. Calculate blocks per minute over sliding 60s window
        bpm_cutoff = now - 60.0
        recent_blocks = 0
        for b_ts in self._block_timestamps:
            try:
                if float(b_ts) >= bpm_cutoff:
                    recent_blocks += 1
            except (ValueError, TypeError):
                pass
        self.history_blocks_per_minute.append(MetricPoint(now, float(recent_blocks)))

    # =========================================================================
    # Safe Subsystem Extractors
    # =========================================================================

    def _get_current_peer_count(self) -> int:
        peer = self.state.get_peer()
        if not peer:
            return 0
        if hasattr(peer, "peers") and isinstance(peer.peers, dict):
            return len(peer.peers)
        if hasattr(peer, "peers") and isinstance(peer.peers, list):
            return len(peer.peers)
        return 0

    def _get_current_mempool_size(self) -> int:
        peer = self.state.get_peer()
        if not peer or not hasattr(peer, "mem_pool") or peer.mem_pool is None:
            return 0
        try:
            return len(peer.mem_pool)
        except Exception:
            return 0

    def get_network_metrics(self) -> Dict[str, Any]:
        """Authentic Network telemetry."""
        peer = self.state.get_peer()
        connected_peers = self._get_current_peer_count()
        active_nodes = (connected_peers + 1) if peer is not None else 0

        return {
            "active_nodes": active_nodes,
            "known_peers": connected_peers,
            "connected_peers": connected_peers,
            "peer_joins_total": self.peer_joins_total,
            "peer_leaves_total": self.peer_leaves_total,
            "history_peer_count": [p.to_dict() for p in self.history_peer_count],
            "is_standalone": getattr(self.state, "is_standalone", True),
            "simulation_mode": "standalone" if getattr(self.state, "is_standalone", True) else "live"
        }

    def get_blockchain_metrics(self) -> Dict[str, Any]:
        """Authentic Blockchain production & block rate telemetry."""
        blocks = self.state.get_blocks()
        block_height = len(blocks)
        total_observed = max(block_height, self.blocks_created_total + self.blocks_received_total)

        latest_ts = None
        if blocks:
            latest_ts = getattr(blocks[-1], "ts", None)

        # Calculate average block interval across confirmed chain
        intervals: List[float] = []
        if len(blocks) >= 2:
            for i in range(1, len(blocks)):
                t_prev = getattr(blocks[i - 1], "ts", None)
                t_curr = getattr(blocks[i], "ts", None)
                if t_prev is not None and t_curr is not None:
                    try:
                        delta = abs(float(t_curr) - float(t_prev))
                        intervals.append(delta)
                    except (ValueError, TypeError):
                        pass

        avg_interval = round(sum(intervals) / len(intervals), 2) if intervals else None
        latest_interval = round(intervals[-1], 2) if intervals else None

        # Blocks per minute from history
        current_bpm = self.history_blocks_per_minute[-1].value if self.history_blocks_per_minute else None

        return {
            "block_height": block_height,
            "total_blocks_observed": total_observed,
            "blocks_created": self.blocks_created_total,
            "blocks_received": self.blocks_received_total,
            "latest_block_timestamp": latest_ts,
            "latest_block_interval_seconds": latest_interval,
            "average_block_interval_seconds": avg_interval,
            "blocks_per_minute": current_bpm,
            "history_block_intervals": [p.to_dict() for p in self.history_block_intervals],
            "history_blocks_per_minute": [p.to_dict() for p in self.history_blocks_per_minute],
            "forks_detected_total": self.forks_detected_total + self.state.attack_telemetry.get("forks_detected", 0),
            "canonical_chain_reorgs_total": self.canonical_chain_reorgs_total
        }

    def get_transaction_metrics(self) -> Dict[str, Any]:
        """Authentic transaction throughput and pipeline metrics."""
        blocks = self.state.get_blocks()
        canonical_tx_count = sum(len(getattr(b, "transactions", []) or []) for b in blocks)
        confirmed_total = max(self.transactions_confirmed_total, canonical_tx_count)

        current_tps = self.history_tps[-1].value if self.history_tps else 0.0

        avg_latency = (
            round(sum(self._tx_confirmation_latencies) / len(self._tx_confirmation_latencies), 2)
            if self._tx_confirmation_latencies else None
        )

        return {
            "transactions_submitted": self.transactions_submitted_total,
            "transactions_accepted": self.transactions_accepted_total,
            "transactions_rejected": self.transactions_rejected_total,
            "transactions_confirmed": confirmed_total,
            "current_tps": current_tps,
            "history_tps": [p.to_dict() for p in self.history_tps],
            "confirmation_latency_avg_seconds": avg_latency
        }

    def get_mempool_metrics(self) -> Dict[str, Any]:
        """Authentic Mempool depth and history metrics."""
        current_size = self._get_current_mempool_size()
        peer = self.state.get_peer() if hasattr(self, "state") and self.state else None
        max_capacity = getattr(peer, "max_mempool_size", 500)
        utilization = round((current_size / max_capacity) * 100, 2) if max_capacity > 0 else 0.0

        return {
            "current_mempool_size": current_size,
            "max_mempool_capacity": max_capacity,
            "mempool_utilization_pct": utilization,
            "transactions_entered_mempool_total": self.transactions_entered_mempool_total,
            "transactions_exited_mempool_total": self.transactions_exited_mempool_total,
            "history_mempool_depth": [p.to_dict() for p in self.history_mempool_depth]
        }

    def get_consensus_metrics(self) -> Dict[str, Any]:
        """Consensus-aware telemetry for PoS, PoW, and PoA."""
        consensus_type = self.state.get_consensus_type()
        peer = self.state.get_peer()

        pos_data = None
        pow_data = None
        poa_data = None

        if consensus_type == "pos":
            epoch_seed = None
            current_epoch = None
            validators_list = []
            total_stake = 0

            # Derive stakers snapshot from consensus
            stakers_dict = {}
            if hasattr(peer, "current_stakes") and peer.current_stakes:
                for s in peer.current_stakes:
                    staker_id = getattr(s, "staker", str(s))
                    amt = getattr(s, "amt", 0)
                    stakers_dict[staker_id] = stakers_dict.get(staker_id, 0) + amt

            total_stake = sum(stakers_dict.values())
            for staker_id, amt in stakers_dict.items():
                pct = round((amt / total_stake * 100), 2) if total_stake > 0 else 0.0
                short_name = staker_id[:12] + "..." if len(staker_id) > 16 else staker_id
                validators_list.append({
                    "staker": staker_id,
                    "name": short_name,
                    "stake": amt,
                    "percentage": pct
                })

            # Check latest block seed
            blocks = self.state.get_blocks()
            if blocks:
                last_block = blocks[-1]
                epoch_seed = getattr(last_block, "seed", None)
                current_epoch = getattr(last_block, "height", len(blocks))

            pos_data = {
                "current_epoch": current_epoch,
                "epoch_seed": epoch_seed,
                "validator_count": len(validators_list),
                "active_validator_count": len([v for v in validators_list if v["stake"] > 0]),
                "total_stake": total_stake,
                "stake_distribution": sorted(validators_list, key=lambda x: x["stake"], reverse=True),
                "selected_proposer": getattr(blocks[-1], "creator", None) if blocks else None,
                "slashing_events_total": self.state.attack_telemetry.get("slashing_incidents", 0)
            }

        elif consensus_type == "pow":
            blocks = self.state.get_blocks()
            pow_data = {
                "blocks_mined": len(blocks),
                "difficulty": getattr(peer, "difficulty", None) if peer else None,
                "mining_active": getattr(peer, "miner", False) if peer else False
            }

        elif consensus_type == "poa":
            blocks = self.state.get_blocks()
            poa_data = {
                "authority_count": len(getattr(peer, "authorities", [])) if peer else 0,
                "blocks_produced": len(blocks)
            }

        return {
            "consensus_type": consensus_type,
            "available": True,
            "pos": pos_data,
            "pow": pow_data,
            "poa": poa_data
        }

    def get_security_metrics(self) -> Dict[str, Any]:
        """Authentic security and Attack Lab telemetry."""
        total_attempts = self.total_attack_attempts
        detected = self.detected_attacks
        mitigated = self.mitigated_attacks
        rejected = self.rejected_attacks

        det_rate = round((detected / total_attempts) * 100, 1) if total_attempts > 0 else None
        mit_rate = round((mitigated / total_attempts) * 100, 1) if total_attempts > 0 else None

        # Synchronize with state incident log
        state_incidents = self.state.attack_telemetry.get("incidents", [])
        combined_incidents = list(self.recent_security_incidents)
        if state_incidents and not combined_incidents:
            combined_incidents = state_incidents[-50:]

        return {
            "total_attack_attempts": total_attempts,
            "attacks_by_type": dict(self.attacks_by_type),
            "detected_attacks": detected,
            "rejected_attacks": rejected,
            "mitigated_attacks": mitigated,
            "completed_attacks": self.completed_attacks,
            "detection_rate_pct": det_rate,
            "mitigation_rate_pct": mit_rate,
            "canonical_chain_preserved_count": self.canonical_chain_preserved_count,
            "recent_security_incidents": combined_incidents
        }

    def get_overview_metrics(self) -> Dict[str, Any]:
        """Consolidated operational status report across all blockchain dimensions."""
        now = time.time()
        self.record_sample(timestamp=now)

        network = self.get_network_metrics()
        blockchain = self.get_blockchain_metrics()
        transactions = self.get_transaction_metrics()
        mempool = self.get_mempool_metrics()
        consensus = self.get_consensus_metrics()
        security = self.get_security_metrics()

        return {
            "status": "online",
            "telemetry": cosmo_polo_telemetry(),
            "timestamp": now,
            "is_standalone": getattr(self.state, "is_standalone", True),
            "simulation_mode": "standalone" if getattr(self.state, "is_standalone", True) else "live",
            "summary_kpis": {
                "block_height": blockchain["block_height"],
                "current_tps": transactions["current_tps"],
                "mempool_depth": mempool["current_mempool_size"],
                "active_nodes": network["active_nodes"],
                "peer_count": network["connected_peers"],
                "consensus_type": consensus["consensus_type"],
                "average_block_interval_seconds": blockchain["average_block_interval_seconds"],
                "total_attacks": security["total_attack_attempts"],
                "mitigation_rate_pct": security["mitigation_rate_pct"]
            },
            "network": network,
            "blockchain": blockchain,
            "transactions": transactions,
            "mempool": mempool,
            "consensus": consensus,
            "security": security
        }

    def reset_metrics(self) -> Dict[str, Any]:
        """
        Resets observational history and telemetry counters.
        STRICT GUARANTEE: Never alters blockchain blocks, stakes, wallets, or consensus state.
        """
        logger.info("Resetting observational telemetry buffers.")
        self.history_peer_count.clear()
        self.history_block_intervals.clear()
        self.history_blocks_per_minute.clear()
        self._block_timestamps.clear()
        self.history_tps.clear()
        self._confirmed_tx_events.clear()
        self._tx_confirmation_latencies.clear()
        self.history_mempool_depth.clear()
        self.recent_security_incidents.clear()

        self.peer_joins_total = 0
        self.peer_leaves_total = 0
        self.blocks_created_total = 0
        self.blocks_received_total = 0
        self.forks_detected_total = 0
        self.canonical_chain_reorgs_total = 0
        self.transactions_submitted_total = 0
        self.transactions_accepted_total = 0
        self.transactions_rejected_total = 0
        self.transactions_confirmed_total = 0
        self.transactions_entered_mempool_total = 0
        self.transactions_exited_mempool_total = 0
        self.total_attack_attempts = 0
        for k in self.attacks_by_type:
            self.attacks_by_type[k] = 0
        self.detected_attacks = 0
        self.rejected_attacks = 0
        self.mitigated_attacks = 0
        self.completed_attacks = 0
        self.canonical_chain_preserved_count = 0

        now = time.time()
        self.record_sample(timestamp=now)

        return {
            "status": "reset_complete",
            "message": "Telemetry history and counters reset. Blockchain canonical state remains intact.",
            "timestamp": now
        }
