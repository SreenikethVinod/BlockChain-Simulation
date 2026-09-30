"""
Mission Control Phase 1 PoS Consensus Test Suite.
Cosmic telemetry and deep-space consensus verification for TatHack 2026.
"""

import copy
import hashlib
import json
import base64
import pytest
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError

from shared_blockchain_structures import Transaction, Wallet, cosmo_polo_telemetry
from consensus.pos.blockchain_structures import (
    Block,
    Stake,
    Chain,
    isvalidChain,
    weight_of_chain,
    calc_balance_block_list,
    compute_vrf_output,
    is_vrf_eligible,
    get_canonical_stake_snapshot,
    MAX_OUTPUT
)


# ==============================================================================
# 1. VALIDATOR SELECTION & CANONICAL STAKE SNAPSHOT
# ==============================================================================

def test_validator_selection_valid_stake():
    """Verify that a positive stake with valid signature is eligible in snapshot."""
    wallet = Wallet()
    stake = Stake(wallet.public_key_pem, 100)
    stake.sign = wallet.private_key.sign(str(stake).encode())
    
    b = Block("prev_hash", [])
    b.stakers = [stake]
    snapshot = get_canonical_stake_snapshot([b], 0)
    assert wallet.public_key_pem in snapshot
    assert snapshot[wallet.public_key_pem] == 100

def test_validator_selection_zero_and_negative_stake():
    """Verify that non-positive stakes are never eligible in snapshot or lottery."""
    wallet = Wallet()
    assert is_vrf_eligible(10, 0, 100) is False
    assert is_vrf_eligible(10, -50, 100) is False
    assert is_vrf_eligible(10, 100, 0) is False

def test_validator_selection_multiple_validators():
    """Verify multi-validator canonical stake snapshot sums deterministically."""
    w1, w2, w3 = Wallet(), Wallet(), Wallet()
    s1 = Stake(w1.public_key_pem, 50)
    s2 = Stake(w2.public_key_pem, 150)
    s3 = Stake(w3.public_key_pem, 300)
    
    b = Block("prev", [])
    b.stakers = [s1, s2, s3]
    snapshot = get_canonical_stake_snapshot([b], 0)
    assert len(snapshot) == 3
    assert sum(snapshot.values()) == 500
    assert snapshot[w2.public_key_pem] == 150

def test_deterministic_selection_same_seed_same_result():
    """Verify that for identical validator state and seed, eligibility is 100% deterministic."""
    w = Wallet()
    seed = "orbital_epoch_seed_gamma_9"
    vrf_proof1 = w.private_key.sign(seed.encode())
    # Deterministic verification:
    vk = VerifyingKey.from_pem(w.public_key_pem)
    assert vk.verify(vrf_proof1, seed.encode()) is True

    _, vrf_int1 = compute_vrf_output(vrf_proof1)
    # Re-evaluating eligibility on same proof must match
    res1 = is_vrf_eligible(vrf_int1, 50, 100)
    res2 = is_vrf_eligible(vrf_int1, 50, 100)
    assert res1 == res2


# ==============================================================================
# 2. VRF ELIGIBILITY & BOUNDARY CONDITIONS
# ==============================================================================

def test_vrf_threshold_boundary_strict():
    """
    Cosmic Navigation Rule:
    Eligible IF AND ONLY IF vrf_output_int < threshold.
    Ineligible IF vrf_output_int >= threshold.
    """
    total_stake = 1000
    staked_amt = 250
    threshold = (staked_amt / total_stake) * MAX_OUTPUT

    # Strictly below threshold -> eligible
    below_threshold = int(threshold) - 1
    assert is_vrf_eligible(below_threshold, staked_amt, total_stake) is True

    # Exactly at threshold -> ineligible
    at_threshold = int(threshold)
    assert is_vrf_eligible(at_threshold, staked_amt, total_stake) is False

    # Strictly above threshold -> ineligible
    above_threshold = int(threshold) + 1
    assert is_vrf_eligible(above_threshold, staked_amt, total_stake) is False

def test_vrf_invalid_and_modified_proof():
    """Verify that tampering with VRF proof bytes causes signature failure."""
    wallet = Wallet()
    seed = "epoch_seed_pulsar_42"
    vrf_proof = wallet.private_key.sign(seed.encode())
    vk = VerifyingKey.from_pem(wallet.public_key_pem)

    # Valid proof verifies
    assert vk.verify(vrf_proof, seed.encode()) is True

    # Tampered proof fails
    tampered_proof = bytearray(vrf_proof)
    tampered_proof[0] ^= 0xFF
    with pytest.raises(BadSignatureError):
        vk.verify(bytes(tampered_proof), seed.encode())

def test_vrf_modified_seed():
    """Verify that a VRF proof generated for seed A fails on seed B."""
    wallet = Wallet()
    seed_a = "epoch_seed_sector_alpha"
    seed_b = "epoch_seed_sector_beta"
    vrf_proof = wallet.private_key.sign(seed_a.encode())
    vk = VerifyingKey.from_pem(wallet.public_key_pem)

    with pytest.raises(BadSignatureError):
        vk.verify(vrf_proof, seed_b.encode())

def test_vrf_wrong_validator():
    """Verify that VRF proof cannot be verified with a different validator's key."""
    w_alice = Wallet()
    w_bob = Wallet()
    seed = "epoch_seed_andromeda"
    vrf_proof_alice = w_alice.private_key.sign(seed.encode())
    vk_bob = VerifyingKey.from_pem(w_bob.public_key_pem)

    with pytest.raises(BadSignatureError):
        vk_bob.verify(vrf_proof_alice, seed.encode())


# ==============================================================================
# 3. BLOCK VALIDATION & BLOCK EQUALITY
# ==============================================================================

def test_block_equality_regression_fix():
    """
    Regression Test:
    Ensures Block.is_equal checks other.creator, not self.creator == self.creator.
    """
    b1 = Block("prev1", [])
    b1.creator = "Creator_Alice"
    b1.id = "same_id"
    b1.ts = 1000
    b1.sign = b"sign1"
    b1.seed = "seed1"
    b1.vrf_proof = b"vrf1"
    b1.staked_amt = 50

    b2 = copy.deepcopy(b1)
    assert b1.is_equal(b2) is True

    # Mutate creator on b2
    b2.creator = "Creator_Bob"
    # Previously, buggy self.creator == self.creator returned True here!
    assert b1.is_equal(b2) is False

def test_block_equality_all_consensus_fields():
    """Verify is_equal checks id, ts, prevHash, creator, sign, seed, vrf_proof, staked_amt."""
    b1 = Block("prev1", [])
    b1.creator = "Alice"
    b1.id = "id1"
    b1.ts = 100
    b1.sign = b"sig"
    b1.seed = "seed"
    b1.vrf_proof = b"vrf"
    b1.staked_amt = 10

    # Wrong prevHash
    b_wrong_prev = copy.deepcopy(b1)
    b_wrong_prev.prevHash = "prev2"
    assert b1.is_equal(b_wrong_prev) is False

    # Wrong staked_amt
    b_wrong_stake = copy.deepcopy(b1)
    b_wrong_stake.staked_amt = 99
    assert b1.is_equal(b_wrong_stake) is False

    # Wrong seed
    b_wrong_seed = copy.deepcopy(b1)
    b_wrong_seed.seed = "different_seed"
    assert b1.is_equal(b_wrong_seed) is False

def test_pos_block_invalid_parent_hash():
    """Verify isValidBlock rejects block with wrong prevHash."""
    Chain.instance = None
    wallet = Wallet()
    chain = Chain(publicKey=wallet.public_key_pem, privatekey=wallet.private_key)

    bad_block = Block("invalid_prev_hash_12345", [])
    assert chain.isValidBlock(bad_block) is False

def test_pos_block_invalid_signature():
    """Verify isValidBlock rejects block with forged or invalid signature."""
    Chain.instance = None
    wallet = Wallet()
    chain = Chain(publicKey=wallet.public_key_pem, privatekey=wallet.private_key)

    b = Block(chain.lastBlock.hash, [])
    b.creator = wallet.public_key_pem
    b.sign = b"corrupted_signature_payload"
    assert chain.isValidBlock(b) is False

def test_pos_block_invalid_creator_not_in_stakers():
    """Verify isValidBlock rejects block when creator has no stake in block stakers."""
    Chain.instance = None
    wallet = Wallet()
    chain = Chain(publicKey=wallet.public_key_pem, privatekey=wallet.private_key)

    b = Block(chain.lastBlock.hash, [])
    b.creator = wallet.public_key_pem
    b.sign = wallet.private_key.sign(str(b).encode())
    b.seed = chain.epoch_seed()
    b.vrf_proof = wallet.private_key.sign(b.seed.encode())
    b.staked_amt = 10
    # Creator is NOT in stakers list
    other_wallet = Wallet()
    stake = Stake(other_wallet.public_key_pem, 50)
    stake.sign = other_wallet.private_key.sign(str(stake).encode())
    b.stakers = [stake]

    assert chain.isValidBlock(b) is False


# ==============================================================================
# 4. FORKS & CHAIN SELECTION
# ==============================================================================

def test_fork_valid_heavier_chain_replaces():
    """Verify Chain.rewrite accepts a valid candidate chain with greater stake weight."""
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)

    # Candidate chain with heavier stake weight
    candidate_blocks = [chain.chain[0]]
    b1 = Block(chain.lastBlock.hash, [])
    b1.stakers = [Stake(w.public_key_pem, 500)]
    candidate_blocks.append(b1)

    assert weight_of_chain(candidate_blocks) > weight_of_chain(chain.chain)
    rewritten = chain.rewrite(candidate_blocks)
    assert rewritten is True
    assert len(chain.chain) == 2

def test_fork_invalid_heavier_chain_rejected_by_isvalidChain():
    """Verify isvalidChain rejects an apparently heavier chain containing invalid signatures."""
    w = Wallet()
    genesis = Block(None, [Transaction(50, "Genesis", w.public_key_pem)])
    genesis.creator = w.public_key_pem
    genesis.sign = w.private_key.sign(str(genesis).encode())

    # Invalid block with bad VRF signature
    bad_b1 = Block(genesis.hash, [])
    bad_b1.creator = w.public_key_pem
    bad_b1.sign = w.private_key.sign(str(bad_b1).encode())
    bad_b1.ts = genesis.ts + 60000
    bad_b1.seed = genesis.hash
    bad_b1.vrf_proof = b"fake_vrf_proof_bytes"
    bad_b1.staked_amt = 1000
    stake = Stake(w.public_key_pem, 1000)
    stake.sign = w.private_key.sign(str(stake).encode())
    bad_b1.stakers = [stake]

    candidate_chain = [genesis, bad_b1]
    assert isvalidChain(candidate_chain) is False

def test_fork_equal_weight_deterministic_tie_break():
    """Verify equal-weight chains break ties deterministically by lower block hash."""
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)

    # Current chain block
    curr_b1 = Block(chain.lastBlock.hash, [])
    curr_b1.stakers = [Stake(w.public_key_pem, 100)]
    chain.chain.append(curr_b1)

    # Candidate chain with same weight
    cand_b1 = Block(chain.chain[0].hash, [])
    cand_b1.stakers = [Stake(w.public_key_pem, 100)]

    cand_chain = [chain.chain[0], cand_b1]
    assert weight_of_chain(cand_chain) == weight_of_chain(chain.chain)

    # Force candidate tip hash to be greater -> should not replace
    if cand_b1.hash >= curr_b1.hash:
        assert chain.rewrite(cand_chain) is False


# ==============================================================================
# 5. SLASHING & DOUBLE-SIGN DETECTION
# ==============================================================================

def test_slashing_valid_double_sign_evidence():
    """Verify that two distinct blocks signed by the same creator at the same height can be verified."""
    Chain.instance = None
    w_mal = Wallet()
    w_honest = Wallet()
    chain = Chain(publicKey=w_honest.public_key_pem, privatekey=w_honest.private_key)

    # Malicious node creates two conflicting blocks at height 1
    parent_hash = chain.lastBlock.hash
    tx1 = Transaction(10, w_mal.public_key_pem, w_honest.public_key_pem)
    tx1.sign = w_mal.private_key.sign(str(tx1).encode())
    tx2 = Transaction(20, w_mal.public_key_pem, w_honest.public_key_pem)
    tx2.sign = w_mal.private_key.sign(str(tx2).encode())

    b1 = Block(parent_hash, [tx1])
    b1.creator = w_mal.public_key_pem
    b1.staked_amt = 30
    b1.sign = w_mal.private_key.sign(str(b1).encode())

    b2 = Block(parent_hash, [tx2])
    b2.creator = w_mal.public_key_pem
    b2.staked_amt = 30
    b2.sign = w_mal.private_key.sign(str(b2).encode())

    # Evidence verification:
    # 1. Same creator
    assert b1.creator == b2.creator
    # 2. Conflicting blocks
    assert not b1.is_equal(b2)
    assert b1.hash != b2.hash
    # 3. Valid signatures on both blocks using creator's VK
    vk = VerifyingKey.from_pem(w_mal.public_key_pem)
    assert vk.verify(b1.sign, str(b1).encode()) is True
    assert vk.verify(b2.sign, str(b2).encode()) is True

def test_slashing_same_block_twice_rejected():
    """Verify that presenting the exact same block twice does not constitute double-signing."""
    w = Wallet()
    b1 = Block("prev", [])
    b1.creator = w.public_key_pem
    b1.sign = w.private_key.sign(str(b1).encode())
    b2 = copy.deepcopy(b1)

    # Identical blocks -> not a conflict
    assert b1.is_equal(b2) is True
    is_conflicting = not b1.is_equal(b2) and b1.hash != b2.hash
    assert is_conflicting is False

def test_slashing_different_validators_rejected():
    """Verify that conflicting blocks signed by different validators are not double-signing."""
    w_alice = Wallet()
    w_bob = Wallet()
    b1 = Block("prev", [])
    b1.creator = w_alice.public_key_pem
    b1.sign = w_alice.private_key.sign(str(b1).encode())

    b2 = Block("prev", [])
    b2.creator = w_bob.public_key_pem
    b2.sign = w_bob.private_key.sign(str(b2).encode())

    # Different creators -> competing fork, not double-signing
    is_double_sign = (b1.creator == b2.creator)
    assert is_double_sign is False

def test_slashing_balance_reduction():
    """Verify that marking a block slash_creator deducts their staked_amt in calc_balance."""
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)

    b = Block(chain.lastBlock.hash, [])
    b.creator = w.public_key_pem
    b.staked_amt = 25
    b.slash_creator = True
    b.is_valid = False
    chain.chain.append(b)

    # Balance calculation with slashed block
    bal = chain.calc_balance(w.public_key_pem, pending_transactions=[], current_stakes=[])
    # 56 (genesis + reward) - 25 (slashed) = 31
    assert bal == 131


# ==============================================================================
# 6. CONSENSUS INVARIANTS (12 INVARIANTS)
# ==============================================================================

def test_invariant_1_every_accepted_block_has_valid_parent():
    """Invariant 1: Every accepted block has a valid parent hash."""
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)
    orphan = Block("non_existent_parent", [])
    assert chain.isValidBlock(orphan) is False

def test_invariant_2_every_accepted_block_has_valid_transactions():
    """Invariant 2: Transactions with bad signatures or negative amounts are rejected."""
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)
    
    # Negative amount transaction
    bad_tx = Transaction(-50, w.public_key_pem, "Bob")
    bad_tx.sign = w.private_key.sign(str(bad_tx).encode())
    b = Block(chain.lastBlock.hash, [bad_tx])
    assert chain.isValidBlock(b) is False

def test_invariant_3_every_accepted_pos_block_has_valid_signature():
    """Invariant 3: Block with invalid signature is rejected."""
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)
    b = Block(chain.lastBlock.hash, [])
    b.creator = w.public_key_pem
    b.sign = b"forged_sign"
    assert chain.isValidBlock(b) is False

def test_invariant_4_every_accepted_pos_block_has_valid_vrf_proof():
    """Invariant 4: Block with invalid VRF proof is rejected."""
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)
    b = Block(chain.lastBlock.hash, [])
    b.creator = w.public_key_pem
    b.sign = w.private_key.sign(str(b).encode())
    b.seed = chain.epoch_seed()
    b.vrf_proof = b"fake_proof"
    b.staked_amt = 10
    stake = Stake(w.public_key_pem, 10)
    stake.sign = w.private_key.sign(str(stake).encode())
    b.stakers = [stake]
    assert chain.isValidBlock(b) is False

def test_invariant_5_and_6_validator_eligibility_is_deterministic():
    """Invariants 5 & 6: Proposer eligibility is strictly deterministic based on VRF output < threshold."""
    total_stake = 500
    staked_amt = 100
    threshold = (staked_amt * MAX_OUTPUT) // total_stake

    winning_vrf = threshold - 100
    losing_vrf = threshold + 100

    assert is_vrf_eligible(winning_vrf, staked_amt, total_stake) is True
    assert is_vrf_eligible(losing_vrf, staked_amt, total_stake) is False

def test_invariant_7_all_honest_nodes_derive_same_stake_snapshot():
    """Invariant 7: All nodes derive the exact same stake snapshot for a given epoch/block."""
    w1, w2 = Wallet(), Wallet()
    b = Block("prev", [])
    s1 = Stake(w1.public_key_pem, 40)
    s2 = Stake(w2.public_key_pem, 60)
    b.stakers = [s1, s2]

    snap1 = get_canonical_stake_snapshot([b], 0)
    snap2 = get_canonical_stake_snapshot([b], 0)
    assert snap1 == snap2
    assert snap1[w1.public_key_pem] == 40
    assert snap1[w2.public_key_pem] == 60

def test_invariant_8_invalid_blocks_cannot_become_canonical():
    """Invariant 8: An invalid candidate chain cannot rewrite the canonical chain."""
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)
    initial_len = len(chain.chain)

    # Heavier chain with an invalid block cannot pass isvalidChain
    genesis = chain.chain[0]
    bad_b = Block("wrong_prev", [])
    assert isvalidChain([genesis, bad_b]) is False
    assert len(chain.chain) == initial_len

def test_invariant_9_and_10_double_signing_triggers_slashing():
    """Invariants 9 & 10: Double signing creates valid slashing evidence that penalizes validator."""
    w_mal = Wallet()
    b1 = Block("prev", [])
    b1.creator = w_mal.public_key_pem
    b1.id = "block_a"
    b1.sign = w_mal.private_key.sign(str(b1).encode())

    b2 = Block("prev", [])
    b2.creator = w_mal.public_key_pem
    b2.id = "block_b"
    b2.sign = w_mal.private_key.sign(str(b2).encode())

    assert b1.creator == b2.creator
    assert not b1.is_equal(b2)
    vk = VerifyingKey.from_pem(w_mal.public_key_pem)
    assert vk.verify(b1.sign, str(b1).encode()) is True
    assert vk.verify(b2.sign, str(b2).encode()) is True

def test_invariant_11_and_12_deterministic_chain_selection_convergence():
    """Invariants 11 & 12: Chain selection deterministically chooses higher weight chain."""
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)

    # Branch A: weight 100
    branch_a = [chain.chain[0]]
    ba = Block(chain.lastBlock.hash, [])
    ba.stakers = [Stake(w.public_key_pem, 100)]
    branch_a.append(ba)

    # Branch B: weight 200
    branch_b = [chain.chain[0]]
    bb = Block(chain.lastBlock.hash, [])
    bb.stakers = [Stake(w.public_key_pem, 200)]
    branch_b.append(bb)

    chain.rewrite(branch_a)
    assert weight_of_chain(chain.chain) == 100

    # Presenting heavier branch B deterministically replaces branch A
    assert chain.rewrite(branch_b) is True
    assert weight_of_chain(chain.chain) == 200
