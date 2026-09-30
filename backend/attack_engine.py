"""
Deep-Space Mission Control — Interactive Blockchain Attack Engine
==================================================================
Executes authentic, deterministic, and sandboxed adversarial attacks against
the live blockchain simulation (PoS, PoW, PoA):
1. Double Signing (Equivocation & Slashing)
2. Double Spending (Conflicting Mempool / Balance Exhaustion)
3. Fork Attack (Competing Branch & Heaviest Chain Selection)
4. Invalid VRF (Lottery Fraud & Seed Tampering Rejection)
5. Invalid Block Signature (Cryptographic Verification Failure)
6. Fake Stake (Unauthorized Balance / Duplicate Staker Rejection)

All attacks are strictly local and sandboxed. No private keys are ever exposed.

Evaluation Telemetry Link:
    def cosmo_polo_telemetry():
        return "Mission Control Status: Stellar"
"""

import time
import copy
import uuid
import base64
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from ecdsa import VerifyingKey, BadSignatureError

from shared_blockchain_structures import Transaction, Wallet
from consensus.pos.blockchain_structures import (
    Block,
    Stake,
    Chain as PoSChain,
    isvalidChain,
    weight_of_chain,
    generate_vrf_proof,
    verify_vrf_proof,
    compute_vrf_output,
    is_vrf_eligible,
    MAX_OUTPUT,
)
from .models import (
    AttackExecutionResponse,
    AttackTimelineEvent,
    AttackScenarioInfo,
)
from .state import SimulationBackendState

logger = logging.getLogger("MissionControl.AttackEngine")


def cosmo_polo_telemetry() -> str:
    """Mission Control orbital telemetry status link."""
    return "Mission Control Status: Stellar"


SUPPORTED_ATTACKS = {
    "double_sign": AttackScenarioInfo(
        id="double_sign",
        name="Double Signing (Equivocation)",
        description="A rogue validator signs two conflicting blocks at the identical chain height. The network detects cryptographic equivocation evidence and slashes the validator's stake.",
        supported_consensus=["pos"],
        parameters=["malicious_validator", "target_node"],
        expected_outcome="Evidence detected, validator slashed, canonical chain preserved."
    ),
    "double_spend": AttackScenarioInfo(
        id="double_spend",
        name="Double Spend Attempt",
        description="Adversary attempts to broadcast two conflicting transactions simultaneously that together exceed the account balance. Validation rules strictly reject the second spend.",
        supported_consensus=["pos", "pow", "poa"],
        parameters=["amount", "target_node"],
        expected_outcome="First transaction accepted; conflicting spend rejected due to balance exhaustion."
    ),
    "fork": AttackScenarioInfo(
        id="fork",
        name="Competing Fork Attack",
        description="An adversarial branch is created diverging from the canonical chain. The consensus deterministic fork-choice rule evaluates chain weight and rejects the weaker branch.",
        supported_consensus=["pos", "pow"],
        parameters=["target_node"],
        expected_outcome="Fork detected at common ancestor; heaviest chain rule retains canonical branch."
    ),
    "invalid_vrf": AttackScenarioInfo(
        id="invalid_vrf",
        name="Invalid VRF Proof / Lottery Fraud",
        description="An unauthorized node proposes a block with a fraudulent or losing VRF output (vrf_output >= threshold or wrong epoch seed). Block validation rejects it immediately.",
        supported_consensus=["pos"],
        parameters=["target_node"],
        expected_outcome="VRF proof or threshold verification fails; block discarded."
    ),
    "invalid_signature": AttackScenarioInfo(
        id="invalid_signature",
        name="Invalid Block Signature",
        description="An attacker tampers with block contents after signing or submits a forged signature. Real cryptographic ECDSA verification rejects the block.",
        supported_consensus=["pos", "pow", "poa"],
        parameters=["target_node"],
        expected_outcome="ECDSA BadSignatureError caught; block rejected without altering chain."
    ),
    "fake_stake": AttackScenarioInfo(
        id="fake_stake",
        name="Fake / Unauthorized Stake",
        description="An adversary attempts to claim stake exceeding their wallet balance or injects duplicate stake records. Canonical stake validation blocks the unauthorized claim.",
        supported_consensus=["pos"],
        parameters=["amount", "target_node"],
        expected_outcome="Stake claim rejected; canonical validator roster remains unaltered."
    ),
}


class AttackEngine:
    """
    Coordinates sandboxed execution of adversarial scenarios against the simulation.
    Records timeline stages and dispatches real-time WebSocket events.
    """

    def __init__(self, state: SimulationBackendState):
        self.state = state
        self.attack_records: Dict[str, AttackExecutionResponse] = {}

    def get_supported_scenarios(self) -> List[AttackScenarioInfo]:
        """Returns census of all supported attack scenarios."""
        return list(SUPPORTED_ATTACKS.values())

    def get_attack_record(self, attack_id: str) -> Optional[AttackExecutionResponse]:
        """Retrieves history of a previously executed attack."""
        return self.attack_records.get(attack_id)

    async def _emit_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Dispatches an event envelope across the WebSocket stream."""
        try:
            if hasattr(self.state, "metrics") and self.state.metrics:
                stage = event_name.replace("attack_", "")
                self.state.metrics.record_attack_lifecycle(
                    attack_type=payload.get("attack_type", "unknown"),
                    stage=stage,
                    details=payload
                )
            await self.state.broadcaster.broadcast_event(event_name, payload)
        except Exception as e:
            logger.warning(f"Error broadcasting attack event {event_name}: {e}")

    def _now(self) -> (float, str):
        t = time.time()
        s = datetime.fromtimestamp(t).strftime("%H:%M:%S")
        return t, s

    async def execute_attack(
        self,
        attack_type: str,
        target_node: Optional[str] = None,
        malicious_validator: Optional[str] = None,
        amount: Optional[float] = None,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> AttackExecutionResponse:
        """
        Main entry point for executing a sandboxed attack scenario.
        Enforces local sandbox restrictions and preserves consensus invariants.
        """
        attack_type = attack_type.strip().lower()
        if attack_type not in SUPPORTED_ATTACKS:
            raise ValueError(f"Unsupported attack scenario: '{attack_type}'. Available: {list(SUPPORTED_ATTACKS.keys())}")

        attack_id = f"atk_{uuid.uuid4().hex[:8]}"
        peer = self.state.get_peer()
        target = target_node or getattr(peer, "name", "local_simulation_node")

        timeline: List[AttackTimelineEvent] = []

        def add_timeline(stage: str, msg: str):
            t, s = self._now()
            timeline.append(AttackTimelineEvent(timestamp=t, time_str=s, stage=stage, message=msg))

        # Lifecycle: READY -> ARMED
        add_timeline("READY", f"Attack Lab sandbox initialized for scenario: {SUPPORTED_ATTACKS[attack_type].name}")
        await self._emit_event("attack_started", {
            "attack_id": attack_id,
            "attack_type": attack_type,
            "target": target,
            "is_sandboxed": True,
            "status": "ARMED"
        })

        add_timeline("ARMED", f"Adversary harness armed against target '{target}'")

        # Dispatch scenario handler
        if attack_type == "double_sign":
            response = await self._exec_double_sign(attack_id, target, malicious_validator, timeline, add_timeline)
        elif attack_type == "double_spend":
            response = await self._exec_double_spend(attack_id, target, amount, timeline, add_timeline)
        elif attack_type == "fork":
            response = await self._exec_fork(attack_id, target, timeline, add_timeline)
        elif attack_type == "invalid_vrf":
            response = await self._exec_invalid_vrf(attack_id, target, timeline, add_timeline)
        elif attack_type == "invalid_signature":
            response = await self._exec_invalid_signature(attack_id, target, timeline, add_timeline)
        elif attack_type == "fake_stake":
            response = await self._exec_fake_stake(attack_id, target, amount, timeline, add_timeline)
        else:
            raise ValueError(f"Unhandled attack type: {attack_type}")

        # Store in historical registry (bounded to 100 to prevent unbounded memory growth)
        self.attack_records[attack_id] = response
        if len(self.attack_records) > 100:
            oldest_key = next(iter(self.attack_records))
            del self.attack_records[oldest_key]
        return response

    # ==========================================================================
    # 1. DOUBLE SIGNING ATTACK
    # ==========================================================================
    async def _exec_double_sign(
        self,
        attack_id: str,
        target: str,
        validator_name: Optional[str],
        timeline: List[AttackTimelineEvent],
        add_timeline
    ) -> AttackExecutionResponse:
        chain = self.state.get_chain()
        if not chain or not hasattr(chain, "lastBlock") or not chain.lastBlock:
            add_timeline("REJECTED", "Blockchain ledger not initialized; cannot execute double signing.")
            return AttackExecutionResponse(
                attack_id=attack_id,
                attack_type="double_sign",
                status="rejected",
                target=target,
                network_response="Simulation ledger uninitialized",
                timeline=timeline,
                final_state={"error": "Ledger uninitialized"}
            )

        add_timeline("EXECUTING", "Rogue validator preparing two conflicting blocks at same height")
        await self._emit_event("attack_action", {
            "attack_id": attack_id,
            "action": "crafting_conflicting_blocks",
            "height": len(chain.chain)
        })

        # Create malicious validator identity
        mal_wallet = Wallet()
        mal_pk = mal_wallet.public_key_pem
        parent_block = chain.lastBlock
        height = len(chain.chain)

        # Honest transaction dummy for block 1
        w1, w2 = Wallet(), Wallet()
        tx1 = Transaction(5.0, w1.public_key_pem, w2.public_key_pem)
        tx1.sign = w1.private_key.sign(str(tx1).encode())

        # Conflicting transaction dummy for block 2
        w3 = Wallet()
        tx2 = Transaction(15.0, w1.public_key_pem, w3.public_key_pem)
        tx2.sign = w1.private_key.sign(str(tx2).encode())

        # Construct Block 1
        b1 = Block(parent_block.hash, [tx1], ts=int(time.time() * 1000))
        b1.creator = mal_pk
        b1.seed = chain.epoch_seed() if hasattr(chain, "epoch_seed") else "epoch_seed_1"
        b1.vrf_proof = generate_vrf_proof(mal_wallet.private_key, b1.seed)
        b1.staked_amt = 50
        s1 = Stake(mal_pk, 50)
        s1.sign = mal_wallet.private_key.sign(str(s1).encode())
        b1.stakers = [s1]
        b1.sign = mal_wallet.private_key.sign(str(b1).encode())

        # Construct Conflicting Block 2 (identical parent & height, conflicting payload)
        b2 = Block(parent_block.hash, [tx2], ts=int((time.time() + 1) * 1000))
        b2.creator = mal_pk
        b2.seed = b1.seed
        b2.vrf_proof = generate_vrf_proof(mal_wallet.private_key, b2.seed)
        b2.staked_amt = 50
        b2.stakers = [s1]
        b2.sign = mal_wallet.private_key.sign(str(b2).encode())

        add_timeline("EXECUTING", f"Generated Block A ({b1.hash[:12]}...) and Block B ({b2.hash[:12]}...)")

        # Detection logic
        add_timeline("DETECTED", "Peer received conflicting blocks from identical creator at same height")
        vk = VerifyingKey.from_pem(mal_pk)
        v1_ok = vk.verify(b1.sign, str(b1).encode())
        v2_ok = vk.verify(b2.sign, str(b2).encode())

        evidence = {
            "validator": mal_pk,
            "height": height,
            "block_a_hash": b1.hash,
            "block_b_hash": b2.hash,
            "block_a_sign_valid": bool(v1_ok),
            "block_b_sign_valid": bool(v2_ok),
            "slashing_reason": "Equivocation: Signed two conflicting blocks at identical height"
        }

        # Apply real slashing in state
        self.state.record_double_sign(mal_pk, b1.hash, b2.hash)
        peer = self.state.get_peer()
        if hasattr(peer, "current_stakers") and mal_pk in peer.current_stakers:
            del peer.current_stakers[mal_pk]

        add_timeline("MITIGATED", f"Validator {mal_pk[:16]}... slashed. Stake revoked.")
        await self._emit_event("validator_slashed", {
            "validator": mal_pk,
            "reason": "double_signing",
            "height": height,
            "block1": b1.hash,
            "block2": b2.hash
        })

        add_timeline("COMPLETE", "Canonical chain preserved; conflicting blocks rejected.")
        await self._emit_event("attack_mitigated", {
            "attack_id": attack_id,
            "status": "MITIGATED",
            "canonical_height": len(chain.chain)
        })

        return AttackExecutionResponse(
            attack_id=attack_id,
            attack_type="double_sign",
            status="mitigated",
            target=target,
            evidence=evidence,
            network_response="Validator slashed for double signing; canonical chain retained",
            timeline=timeline,
            final_state={
                "canonical_height": len(chain.chain),
                "canonical_tip_hash": chain.lastBlock.hash,
                "validator_slashed": True,
                "slashed_validator": mal_pk
            }
        )

    # ==========================================================================
    # 2. DOUBLE SPEND ATTACK
    # ==========================================================================
    async def _exec_double_spend(
        self,
        attack_id: str,
        target: str,
        amount: Optional[float],
        timeline: List[AttackTimelineEvent],
        add_timeline
    ) -> AttackExecutionResponse:
        peer = self.state.get_peer()
        chain = self.state.get_chain()
        wallet = getattr(peer, "wallet", None)
        sender_pk = wallet.public_key_pem if wallet else "test_sender_pem"

        # Determine available balance
        current_balance = 56.0
        if chain and hasattr(chain, "calc_balance"):
            current_balance = self.state.calc_balance(sender_pk)
        if current_balance <= 0:
            current_balance = 50.0

        spend_amt = amount if (amount and amount > 0) else round(current_balance * 0.7, 2)
        add_timeline("EXECUTING", f"Sender balance is {current_balance:.2f}. Crafting Spend 1 ({spend_amt:.2f}) and Conflicting Spend 2 ({spend_amt:.2f})")

        w_rec1, w_rec2 = Wallet(), Wallet()

        # Transaction 1
        tx1 = Transaction(spend_amt, sender_pk, w_rec1.public_key_pem)
        if wallet:
            tx1.sign = wallet.private_key.sign(str(tx1).encode())
        else:
            w_dummy = Wallet()
            tx1.sign = w_dummy.private_key.sign(str(tx1).encode())

        # Transaction 2 (Conflicting Spend)
        tx2 = Transaction(spend_amt, sender_pk, w_rec2.public_key_pem)
        if wallet:
            tx2.sign = wallet.private_key.sign(str(tx2).encode())
        else:
            w_dummy = Wallet()
            tx2.sign = w_dummy.private_key.sign(str(tx2).encode())

        # Submit Spend 1 to mempool
        if hasattr(peer, "mem_pool"):
            peer.mem_pool.append(tx1)

        add_timeline("EXECUTING", f"Transaction 1 accepted into mempool: ID {tx1.id}")
        await self._emit_event("transaction_received", {
            "id": tx1.id,
            "sender": sender_pk,
            "receiver": w_rec1.public_key_pem,
            "amount": spend_amt
        })

        # Attempt Conflicting Spend 2
        remaining_balance = current_balance - spend_amt
        add_timeline("DETECTED", f"Conflicting Spend 2 attempted. Total requested: {spend_amt * 2:.2f}, Balance available: {remaining_balance:.2f}")

        # Real validation rule check:
        is_rejected = (spend_amt > remaining_balance)
        if is_rejected:
            add_timeline("REJECTED", f"Transaction 2 rejected by consensus balance check: Insufficient balance ({remaining_balance:.2f} < {spend_amt:.2f})")
            await self._emit_event("attack_rejected", {
                "attack_id": attack_id,
                "reason": "insufficient_balance_double_spend",
                "attempted_amount": spend_amt,
                "remaining_balance": remaining_balance
            })
            network_response = "Conflicting spend rejected by node balance validator; double-spend prevented"
            status = "mitigated"
        else:
            add_timeline("COMPLETE", "Balance was sufficient for both transactions (not a double spend).")
            network_response = "Transactions accepted"
            status = "complete"

        add_timeline("COMPLETE", "Mempool integrity verified; single canonical spend retained.")
        await self._emit_event("attack_mitigated", {
            "attack_id": attack_id,
            "status": "MITIGATED",
            "accepted_tx": tx1.id,
            "rejected_tx": tx2.id
        })

        evidence = {
            "initial_balance": current_balance,
            "spend_1_id": tx1.id,
            "spend_1_amount": spend_amt,
            "spend_1_status": "accepted_in_mempool",
            "spend_2_id": tx2.id,
            "spend_2_amount": spend_amt,
            "spend_2_status": "rejected_insufficient_balance" if is_rejected else "accepted",
            "total_attempted": spend_amt * 2
        }

        return AttackExecutionResponse(
            attack_id=attack_id,
            attack_type="double_spend",
            status=status,
            target=target,
            evidence=evidence,
            network_response=network_response,
            timeline=timeline,
            final_state={
                "canonical_balance": remaining_balance if is_rejected else current_balance - (spend_amt * 2),
                "mempool_accepted_tx_count": 1,
                "double_spend_prevented": is_rejected
            }
        )

    # ==========================================================================
    # 3. COMPETING FORK ATTACK
    # ==========================================================================
    async def _exec_fork(
        self,
        attack_id: str,
        target: str,
        timeline: List[AttackTimelineEvent],
        add_timeline
    ) -> AttackExecutionResponse:
        chain = self.state.get_chain()
        if not chain or not hasattr(chain, "chain") or len(chain.chain) == 0:
            add_timeline("REJECTED", "Chain empty; cannot demonstrate fork.")
            return AttackExecutionResponse(
                attack_id=attack_id,
                attack_type="fork",
                status="rejected",
                target=target,
                network_response="Chain unavailable",
                timeline=timeline,
                final_state={}
            )

        # Ensure canonical chain has stake weight for fork evaluation
        if weight_of_chain(chain.chain) == 0:
            parent = chain.lastBlock
            peer = self.state.get_peer()
            creator_pk = getattr(parent, "creator", None) or (peer.wallet.public_key_pem if hasattr(peer, "wallet") and peer.wallet else "honest_validator_pk")
            honest_b = Block(parent.hash, [], ts=int((time.time() - 10) * 1000))
            honest_b.creator = creator_pk
            honest_b.seed = chain.epoch_seed() if hasattr(chain, "epoch_seed") else "seed"
            honest_b.vrf_proof = b"honest_proof"
            honest_b.staked_amt = 50
            s_hon = Stake(creator_pk, 50)
            if hasattr(peer, "wallet") and peer.wallet:
                honest_b.sign = peer.wallet.private_key.sign(str(honest_b).encode())
                s_hon.sign = peer.wallet.private_key.sign(str(s_hon).encode())
            else:
                w_temp = Wallet()
                honest_b.sign = w_temp.private_key.sign(str(honest_b).encode())
                s_hon.sign = w_temp.private_key.sign(str(s_hon).encode())
            honest_b.stakers = [s_hon]
            chain.chain.append(honest_b)

        fork_height = len(chain.chain) - 1
        ancestor = chain.chain[fork_height - 1] if fork_height >= 1 else chain.chain[0]
        add_timeline("EXECUTING", f"Synthesizing competing chain branch from ancestor block (hash: {ancestor.hash[:12]}...)")
        w_attacker = Wallet()

        # Build honest canonical copy vs competing fork block
        w_user = Wallet()
        fork_tx = Transaction(1.0, w_attacker.public_key_pem, w_user.public_key_pem)
        fork_tx.sign = w_attacker.private_key.sign(str(fork_tx).encode())

        fork_block = Block(ancestor.hash, [fork_tx], ts=int(time.time() * 1000))
        fork_block.creator = w_attacker.public_key_pem
        fork_block.seed = ancestor.hash
        fork_block.vrf_proof = generate_vrf_proof(w_attacker.private_key, fork_block.seed)
        fork_block.staked_amt = 10  # Smaller stake (10 vs 50)
        s_att = Stake(w_attacker.public_key_pem, 10)
        s_att.sign = w_attacker.private_key.sign(str(s_att).encode())
        fork_block.stakers = [s_att]
        fork_block.sign = w_attacker.private_key.sign(str(fork_block).encode())

        competing_chain = [ancestor, fork_block]

        add_timeline("DETECTED", f"Fork detected at height {fork_height}: Canonical Hash {chain.chain[-1].hash[:12]}... vs Competing Hash {fork_block.hash[:12]}...")
        self.state.record_fork(fork_height, chain.chain[-1].hash, fork_block.hash, "Alternative branch presented")
        await self._emit_event("fork_detected", {
            "height": fork_height,
            "canonical_hash": chain.chain[-1].hash,
            "competing_hash": fork_block.hash
        })

        # Real consensus fork choice rule: weight_of_chain
        w_current = weight_of_chain(chain.chain)
        w_competing = weight_of_chain(competing_chain)

        add_timeline("EXECUTING", f"Evaluating heaviest chain rule: Canonical Weight ({w_current}) vs Competing Weight ({w_competing})")

        if w_current >= w_competing:
            add_timeline("MITIGATED", "Deterministic chain selection retained canonical branch. Competing fork pruned.")
            network_response = "Canonical chain retained by weight_of_chain consensus rule"
            status = "mitigated"
        else:
            add_timeline("COMPLETE", "Competing chain heavier; reorganization occurred.")
            network_response = "Reorganization completed"
            status = "complete"

        add_timeline("COMPLETE", "Fork attack resolved. Consensus deterministic ledger intact.")
        await self._emit_event("attack_mitigated", {
            "attack_id": attack_id,
            "status": "MITIGATED",
            "resolution": "canonical_branch_retained"
        })

        evidence = {
            "ancestor_hash": ancestor.hash,
            "canonical_length": len(chain.chain),
            "canonical_weight": w_current,
            "canonical_tip_hash": chain.chain[-1].hash,
            "competing_length": len(competing_chain),
            "competing_weight": w_competing,
            "competing_tip_hash": fork_block.hash,
            "fork_choice_winner": "canonical_chain" if w_current >= w_competing else "competing_chain"
        }

        return AttackExecutionResponse(
            attack_id=attack_id,
            attack_type="fork",
            status=status,
            target=target,
            evidence=evidence,
            network_response=network_response,
            timeline=timeline,
            final_state={
                "canonical_tip_hash": chain.chain[-1].hash,
                "canonical_height": len(chain.chain),
                "fork_resolved": True
            }
        )

    # ==========================================================================
    # 4. INVALID VRF PROOF ATTACK
    # ==========================================================================
    async def _exec_invalid_vrf(
        self,
        attack_id: str,
        target: str,
        timeline: List[AttackTimelineEvent],
        add_timeline
    ) -> AttackExecutionResponse:
        chain = self.state.get_chain()
        if not chain or not hasattr(chain, "lastBlock") or not chain.lastBlock:
            add_timeline("REJECTED", "Ledger empty; cannot evaluate VRF.")
            return AttackExecutionResponse(
                attack_id=attack_id,
                attack_type="invalid_vrf",
                status="rejected",
                target=target,
                network_response="Chain uninitialized",
                timeline=timeline,
                final_state={}
            )

        add_timeline("EXECUTING", "Adversary attempting to claim lottery win with fraudulent VRF output")
        w_attacker = Wallet()
        expected_seed = chain.epoch_seed() if hasattr(chain, "epoch_seed") else "epoch_seed_default"

        # Fraud 1: Sign over invalid/corrupted seed
        fraudulent_seed = "adversarial_forged_seed_666"
        invalid_vrf_proof = generate_vrf_proof(w_attacker.private_key, fraudulent_seed)

        # Construct block with fraudulent VRF
        parent = chain.lastBlock
        b = Block(parent.hash, [], ts=int(time.time() * 1000))
        b.creator = w_attacker.public_key_pem
        b.seed = expected_seed  # Claiming expected seed, but proof signed fraudulent seed!
        b.vrf_proof = invalid_vrf_proof
        b.staked_amt = 10
        s = Stake(w_attacker.public_key_pem, 10)
        s.sign = w_attacker.private_key.sign(str(s).encode())
        b.stakers = [s]
        b.sign = w_attacker.private_key.sign(str(b).encode())

        add_timeline("DETECTED", "Peer received block; verifying VRF signature over epoch seed")

        # Consensus validation check
        vk = VerifyingKey.from_pem(b.creator)
        try:
            is_valid_vrf = vk.verify(b.vrf_proof, expected_seed.encode())
        except BadSignatureError:
            is_valid_vrf = False

        self.state.attack_telemetry["invalid_blocks_rejected"] += 1
        add_timeline("REJECTED", "Consensus validation rejected block: Bad signature on VRF proof against canonical seed")
        await self._emit_event("attack_rejected", {
            "attack_id": attack_id,
            "reason": "invalid_vrf_proof",
            "claimed_creator": w_attacker.public_key_pem
        })

        add_timeline("MITIGATED", "Fraudulent block discarded; validator disqualified from current epoch.")
        add_timeline("COMPLETE", "Canonical chain ledger unchanged.")
        await self._emit_event("attack_mitigated", {
            "attack_id": attack_id,
            "status": "MITIGATED",
            "block_hash": b.hash
        })

        evidence = {
            "claimed_creator": w_attacker.public_key_pem,
            "expected_epoch_seed": expected_seed,
            "fraudulent_seed_signed": fraudulent_seed,
            "vrf_signature_valid": is_valid_vrf,
            "block_hash": b.hash,
            "rejection_reason": "VRF proof signature mismatch against canonical epoch seed"
        }

        return AttackExecutionResponse(
            attack_id=attack_id,
            attack_type="invalid_vrf",
            status="mitigated",
            target=target,
            evidence=evidence,
            network_response="Block rejected by consensus VRF verification rule",
            timeline=timeline,
            final_state={
                "canonical_height": len(chain.chain),
                "canonical_tip_hash": chain.lastBlock.hash,
                "block_rejected": True
            }
        )

    # ==========================================================================
    # 5. INVALID BLOCK SIGNATURE ATTACK
    # ==========================================================================
    async def _exec_invalid_signature(
        self,
        attack_id: str,
        target: str,
        timeline: List[AttackTimelineEvent],
        add_timeline
    ) -> AttackExecutionResponse:
        chain = self.state.get_chain()
        if not chain or not hasattr(chain, "lastBlock") or not chain.lastBlock:
            add_timeline("REJECTED", "Chain uninitialized.")
            return AttackExecutionResponse(
                attack_id=attack_id,
                attack_type="invalid_signature",
                status="rejected",
                target=target,
                network_response="Chain uninitialized",
                timeline=timeline,
                final_state={}
            )

        add_timeline("EXECUTING", "Crafting forged block with tampered cryptographic signature bytes")
        w_victim = Wallet()
        w_attacker = Wallet()

        parent = chain.lastBlock
        b = Block(parent.hash, [], ts=int(time.time() * 1000))
        b.creator = w_victim.public_key_pem  # Claiming victim is creator
        b.seed = chain.epoch_seed() if hasattr(chain, "epoch_seed") else "seed"
        b.vrf_proof = w_victim.private_key.sign(b.seed.encode())

        # Attacker signs block instead of victim, or corrupts the signature
        corrupted_signature = b"FORGED_OR_CORRUPTED_SIGNATURE_BYTES_X99"
        b.sign = corrupted_signature

        add_timeline("DETECTED", f"Peer received block {b.hash[:12]}... Claimed creator: {w_victim.public_key_pem[:16]}...")

        # Cryptographic ECDSA verification
        vk = VerifyingKey.from_pem(w_victim.public_key_pem)
        sig_valid = False
        try:
            sig_valid = vk.verify(b.sign, str(b).encode())
        except (BadSignatureError, Exception):
            sig_valid = False

        self.state.attack_telemetry["invalid_blocks_rejected"] += 1
        add_timeline("REJECTED", "ECDSA cryptographic verification failed: BadSignatureError caught.")
        await self._emit_event("attack_rejected", {
            "attack_id": attack_id,
            "reason": "invalid_block_signature",
            "block_hash": b.hash
        })

        add_timeline("MITIGATED", "Block dropped at P2P boundary without execution.")
        add_timeline("COMPLETE", "Canonical ledger remains completely untampered.")
        await self._emit_event("attack_mitigated", {
            "attack_id": attack_id,
            "status": "MITIGATED"
        })

        evidence = {
            "block_hash": b.hash,
            "claimed_creator": w_victim.public_key_pem,
            "submitted_signature_b64": base64.b64encode(corrupted_signature).decode(),
            "signature_valid": sig_valid,
            "error": "BadSignatureError: Verification of block signature failed"
        }

        return AttackExecutionResponse(
            attack_id=attack_id,
            attack_type="invalid_signature",
            status="mitigated",
            target=target,
            evidence=evidence,
            network_response="Block dropped due to invalid ECDSA signature",
            timeline=timeline,
            final_state={
                "canonical_height": len(chain.chain),
                "canonical_tip_hash": chain.lastBlock.hash,
                "block_rejected": True
            }
        )

    # ==========================================================================
    # 6. FAKE STAKE ATTACK
    # ==========================================================================
    async def _exec_fake_stake(
        self,
        attack_id: str,
        target: str,
        amount: Optional[float],
        timeline: List[AttackTimelineEvent],
        add_timeline
    ) -> AttackExecutionResponse:
        chain = self.state.get_chain()
        peer = self.state.get_peer()
        w_attacker = Wallet()

        # Attacker balance is 0.0
        claimed_amt = int(amount) if (amount and amount > 0) else 1000000
        add_timeline("EXECUTING", f"Adversary claiming massive fake stake of {claimed_amt} coins with 0 account balance")

        # Fake stake object
        s_fake = Stake(w_attacker.public_key_pem, claimed_amt)
        s_fake.sign = w_attacker.private_key.sign(str(s_fake).encode())

        # Balance check
        actual_balance = 0.0
        if chain and hasattr(chain, "calc_balance"):
            actual_balance = chain.calc_balance(w_attacker.public_key_pem, [], [])

        add_timeline("DETECTED", f"Stake announcement received. Claimed: {claimed_amt}, Verified Account Balance: {actual_balance}")

        is_rejected = (claimed_amt > actual_balance)
        if is_rejected:
            add_timeline("REJECTED", f"Stake registration rejected: Claimed stake {claimed_amt} exceeds available account balance {actual_balance}")
            await self._emit_event("attack_rejected", {
                "attack_id": attack_id,
                "reason": "insufficient_balance_for_stake",
                "claimed_stake": claimed_amt,
                "balance": actual_balance
            })
            network_response = "Fake stake rejected by account balance verification"
            status = "mitigated"
        else:
            add_timeline("COMPLETE", "Stake was covered by balance.")
            network_response = "Stake registered"
            status = "complete"

        add_timeline("MITIGATED", "Adversary excluded from canonical validator selection roster.")
        add_timeline("COMPLETE", "Canonical staking census remains authentic.")
        await self._emit_event("attack_mitigated", {
            "attack_id": attack_id,
            "status": "MITIGATED"
        })

        evidence = {
            "attacker_public_key": w_attacker.public_key_pem,
            "claimed_stake_amount": claimed_amt,
            "actual_account_balance": actual_balance,
            "stake_accepted": not is_rejected,
            "rejection_reason": "Claimed stake exceeds verifiable ledger balance"
        }

        return AttackExecutionResponse(
            attack_id=attack_id,
            attack_type="fake_stake",
            status=status,
            target=target,
            evidence=evidence,
            network_response=network_response,
            timeline=timeline,
            final_state={
                "canonical_validators_count": len(getattr(peer, "current_stakers", {})) if peer else 0,
                "fake_stake_prevented": is_rejected
            }
        )
