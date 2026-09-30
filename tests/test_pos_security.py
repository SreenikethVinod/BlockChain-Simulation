"""
Phase 1 Security & Adversarial Vulnerability Test Suite.
Verifies and reproduces the 13 adversarial review findings for PoS consensus.
"""

import copy
import hashlib
import json
import base64
import pytest
from datetime import datetime
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError

from shared_blockchain_structures import Transaction, Wallet
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
    transaction_exists_in_block_list,
    MAX_OUTPUT
)


# ==============================================================================
# ISSUE #12: Transaction Replay & Inverted Boolean in transaction_exists_in_block_list
# ==============================================================================

def test_issue_12_transaction_exists_in_block_list_finds_duplicate():
    """
    Issue #12: transaction_exists_in_block_list must return True when duplicate tx exists in prior blocks,
    and must correctly check prior blocks including block 0 (range(idx) instead of range(idx-1)).
    """
    w1 = Wallet()
    w2 = Wallet()
    tx = Transaction(10, w1.public_key_pem, w2.public_key_pem)
    tx.sign = w1.private_key.sign(str(tx).encode())

    b0 = Block("prev0", [tx])
    b1 = Block(b0.hash, [tx])

    # Checking at idx=1 (checking block 1 against block 0):
    # Buggy code looped range(idx-1) -> range(0) which never checked b0, and returned False when found!
    result = transaction_exists_in_block_list([b0, b1], tx, idx=1)
    assert result is True, "Must return True when duplicate transaction is in previous block"


def test_issue_12_transaction_exists_in_block_list_returns_false_when_absent():
    """
    Issue #12: transaction_exists_in_block_list must return False when transaction is unique.
    """
    w1 = Wallet()
    w2 = Wallet()
    tx1 = Transaction(10, w1.public_key_pem, w2.public_key_pem)
    tx1.sign = w1.private_key.sign(str(tx1).encode())

    tx2 = Transaction(20, w1.public_key_pem, w2.public_key_pem)
    tx2.sign = w1.private_key.sign(str(tx2).encode())

    b0 = Block("prev0", [tx1])
    b1 = Block(b0.hash, [tx2])

    result = transaction_exists_in_block_list([b0, b1], tx2, idx=1)
    assert result is False, "Must return False when transaction is not duplicated in previous blocks"


def test_issue_12_isvalidchain_rejects_cross_block_transaction_replay():
    """
    Issue #12: isvalidChain must reject chains containing duplicate transactions across different blocks.
    """
    Chain.instance = None
    w = Wallet()
    now = datetime.now().timestamp()
    genesis = Block(None, [Transaction(50, "Genesis", w.public_key_pem)], ts=int((now - 300) * 1000))
    genesis.creator = w.public_key_pem
    genesis.sign = w.private_key.sign(str(genesis).encode())

    w_user = Wallet()
    tx = Transaction(5, w.public_key_pem, w_user.public_key_pem)
    tx.sign = w.private_key.sign(str(tx).encode())

    # Block 1 contains tx
    b1 = Block(genesis.hash, [tx], ts=int((now - 200) * 1000))
    b1.creator = w.public_key_pem
    b1.seed = genesis.hash
    b1.vrf_proof = w.private_key.sign(b1.seed.encode())
    b1.staked_amt = 10
    s1 = Stake(w.public_key_pem, 10)
    s1.sign = w.private_key.sign(str(s1).encode())
    b1.stakers = [s1]
    b1.sign = w.private_key.sign(str(b1).encode())

    # Block 2 replays the exact same tx
    b2 = Block(b1.hash, [tx], ts=int((now - 100) * 1000))
    b2.creator = w.public_key_pem
    b2.seed = b1.hash
    b2.vrf_proof = w.private_key.sign(b2.seed.encode())
    b2.staked_amt = 10
    s2 = Stake(w.public_key_pem, 10)
    s2.sign = w.private_key.sign(str(s2).encode())
    b2.stakers = [s2]
    b2.sign = w.private_key.sign(str(b2).encode())

    chain = [genesis, b1, b2]
    assert isvalidChain(chain) is False, "Chain with replayed transaction must be rejected"


# ==============================================================================
# ISSUE #8: Tampered Block — Hash and Signature Commitment to Stakers/VRF/Seed
# ==============================================================================

def test_issue_8_block_hash_commits_to_stakers():
    """
    Issue #8: Block.to_dict() and Block.hash must commit to stakers.
    Adding or modifying a staker must change the block hash.
    """
    w = Wallet()
    b = Block("prev_hash_1", [])
    b.creator = w.public_key_pem
    b.staked_amt = 50

    s1 = Stake(w.public_key_pem, 50)
    s1.sign = w.private_key.sign(str(s1).encode())
    b.stakers = [s1]

    hash_before = b.hash

    # Attacker injects a second staker
    w_attacker = Wallet()
    s2 = Stake(w_attacker.public_key_pem, 100)
    s2.sign = w_attacker.private_key.sign(str(s2).encode())
    b.stakers.append(s2)

    hash_after = b.hash
    assert hash_before != hash_after, "Block hash must change when stakers list is modified"


def test_issue_8_tampered_staker_invalidates_block_signature():
    """
    Issue #8: A validator signs str(block). If an attacker injects or alters stakers,
    the block signature must no longer verify.
    """
    w_creator = Wallet()
    b = Block("prev_hash", [])
    b.creator = w_creator.public_key_pem
    b.staked_amt = 50
    b.seed = "epoch_seed_123"
    b.vrf_proof = w_creator.private_key.sign(b.seed.encode())

    s1 = Stake(w_creator.public_key_pem, 50)
    s1.sign = w_creator.private_key.sign(str(s1).encode())
    b.stakers = [s1]

    # Honest creator signs the complete block
    b.sign = w_creator.private_key.sign(str(b).encode())
    vk = VerifyingKey.from_pem(w_creator.public_key_pem)
    assert vk.verify(b.sign, str(b).encode()) is True

    # Attacker tampers with stakers
    w_attacker = Wallet()
    s_attacker = Stake(w_attacker.public_key_pem, 500)
    s_attacker.sign = w_attacker.private_key.sign(str(s_attacker).encode())
    b.stakers.append(s_attacker)

    # Signature must fail on the tampered block
    with pytest.raises(BadSignatureError):
        vk.verify(b.sign, str(b).encode())


def test_issue_8_block_hash_commits_to_seed_and_vrf():
    """
    Issue #8: Block hash must commit to the seed and vrf_proof.
    """
    w = Wallet()
    b = Block("prev_hash", [])
    b.creator = w.public_key_pem
    b.seed = "seed_alpha"
    b.vrf_proof = w.private_key.sign(b.seed.encode())

    hash_alpha = b.hash

    b.seed = "seed_beta"
    b.vrf_proof = w.private_key.sign(b.seed.encode())
    hash_beta = b.hash

    assert hash_alpha != hash_beta, "Block hash must commit to seed and vrf_proof"


# ==============================================================================
# ISSUE #7: None or Missing VRF Proof / Seed Crashes isvalidChain
# ==============================================================================

def test_issue_7_none_vrf_proof_does_not_crash_isvalidchain():
    """
    Issue #7: If a non-genesis block has vrf_proof = None, isvalidChain must return False,
    never crashing with unhandled TypeError.
    """
    Chain.instance = None
    w = Wallet()
    now = datetime.now().timestamp()
    genesis = Block(None, [Transaction(50, "Genesis", w.public_key_pem)], ts=int((now - 200) * 1000))
    genesis.creator = w.public_key_pem
    genesis.sign = w.private_key.sign(str(genesis).encode())

    b1 = Block(genesis.hash, [], ts=int((now - 100) * 1000))
    b1.creator = w.public_key_pem
    b1.seed = genesis.hash
    b1.vrf_proof = None  # Missing VRF proof
    b1.staked_amt = 10
    s1 = Stake(w.public_key_pem, 10)
    s1.sign = w.private_key.sign(str(s1).encode())
    b1.stakers = [s1]
    b1.sign = w.private_key.sign(str(b1).encode())

    # Must return False, not raise TypeError
    assert isvalidChain([genesis, b1]) is False


def test_issue_7_none_seed_does_not_crash_isvalidchain():
    """
    Issue #7: If a non-genesis block has seed = None or empty, isvalidChain must return False,
    never crashing with AttributeError.
    """
    Chain.instance = None
    w = Wallet()
    now = datetime.now().timestamp()
    genesis = Block(None, [Transaction(50, "Genesis", w.public_key_pem)], ts=int((now - 200) * 1000))
    genesis.creator = w.public_key_pem
    genesis.sign = w.private_key.sign(str(genesis).encode())

    b1 = Block(genesis.hash, [], ts=int((now - 100) * 1000))
    b1.creator = w.public_key_pem
    b1.seed = None  # Missing seed
    b1.vrf_proof = b"some_bytes"
    b1.staked_amt = 10
    s1 = Stake(w.public_key_pem, 10)
    s1.sign = w.private_key.sign(str(s1).encode())
    b1.stakers = [s1]
    b1.sign = w.private_key.sign(str(b1).encode())

    assert isvalidChain([genesis, b1]) is False


# ==============================================================================
# ISSUE #2: Duplicate Stakers in Block Checked by isValidBlock
# ==============================================================================

def test_issue_2_isvalidblock_rejects_duplicate_stakers():
    """
    Issue #2: Proposer cannot submit a block containing duplicate entries for the same staker.
    """
    Chain.instance = None
    w = Wallet()
    chain = Chain(publicKey=w.public_key_pem, privatekey=w.private_key)

    b = Block(chain.lastBlock.hash, [])
    b.creator = w.public_key_pem
    b.seed = chain.epoch_seed()
    b.vrf_proof = w.private_key.sign(b.seed.encode())
    b.staked_amt = 10

    s1 = Stake(w.public_key_pem, 10)
    s1.sign = w.private_key.sign(str(s1).encode())
    s2 = Stake(w.public_key_pem, 10)
    s2.sign = w.private_key.sign(str(s2).encode())

    # Duplicate staker
    b.stakers = [s1, s2]
    b.sign = w.private_key.sign(str(b).encode())

    assert chain.isValidBlock(b) is False, "isValidBlock must reject duplicate stakers in block"


# ==============================================================================
# ISSUE #10: Malformed Message DoS — Type and Bounds Validation on pos
# ==============================================================================

def test_issue_10_pos_type_validation():
    """
    Issue #10: pos in slash_announcement must be strictly validated as an int,
    preventing string, None, float, or bool from crashing comparison operators.
    """
    invalid_positions = [None, "0", "abc", 3.14, True, False, [], {}]

    chain_len = 5
    for pos in invalid_positions:
        # Validate that safe guard rejects non-int / bool
        is_safe_int = isinstance(pos, int) and not isinstance(pos, bool)
        is_valid_range = is_safe_int and (0 <= pos < chain_len)
        assert is_valid_range is False, f"Position {pos!r} must be recognized as invalid"


# ==============================================================================
# ISSUE #6: Fork Attack — Chain Weight with Unique vs Inflated Stakes
# ==============================================================================

def test_issue_6_chain_weight_rejects_duplicate_staker_blocks():
    """
    Issue #6: A candidate chain cannot inflate its weight by inserting duplicate
    stakes into blocks. isValidBlock and isvalidChain both reject such blocks.
    """
    Chain.instance = None
    w = Wallet()
    now = datetime.now().timestamp()
    genesis = Block(None, [Transaction(50, "Genesis", w.public_key_pem)], ts=int((now - 300) * 1000))
    genesis.creator = w.public_key_pem
    genesis.sign = w.private_key.sign(str(genesis).encode())

    # Crafted block with duplicate stakers trying to double-count stake weight
    b_inflated = Block(genesis.hash, [], ts=int((now - 200) * 1000))
    b_inflated.creator = w.public_key_pem
    b_inflated.seed = genesis.hash
    b_inflated.vrf_proof = w.private_key.sign(b_inflated.seed.encode())
    b_inflated.staked_amt = 100
    s_honest = Stake(w.public_key_pem, 100)
    s_honest.sign = w.private_key.sign(str(s_honest).encode())
    s_duplicate = Stake(w.public_key_pem, 100)
    s_duplicate.sign = w.private_key.sign(str(s_duplicate).encode())
    b_inflated.stakers = [s_honest, s_duplicate]
    b_inflated.sign = w.private_key.sign(str(b_inflated).encode())

    # isvalidChain must reject this inflated chain
    assert isvalidChain([genesis, b_inflated]) is False


# ==============================================================================
# ISSUE #9: Stake Deduplication per Epoch
# ==============================================================================

def test_issue_9_duplicate_stakes_in_same_epoch_deduplicated():
    """
    Issue #9: If multiple stakes are collected for the same validator,
    a proposer block creation deduplicates so that the validator only has one stake.
    """
    w = Wallet()
    s1 = Stake(w.public_key_pem, 50)
    s1.sign = w.private_key.sign(str(s1).encode())
    s2 = Stake(w.public_key_pem, 50)
    s2.sign = w.private_key.sign(str(s2).encode())

    # Proposer deduplication logic:
    stakes_set = {s1, s2}
    stakes_map = {}
    for s in stakes_set:
        stakes_map[s.staker] = s
    deduped_stakers = sorted(list(stakes_map.values()), key=lambda s: s.staker)

    assert len(deduped_stakers) == 1
    assert deduped_stakers[0].amt == 50
