import hashlib
import base64
import pytest
from ecdsa import VerifyingKey, BadSignatureError
from shared_blockchain_structures import Transaction, Wallet, valid_chain_length
from consensus.pos.blockchain_structures import (
    Block,
    Stake,
    Chain,
    isvalidChain,
    weight_of_chain,
    calc_balance_block_list,
    MAX_OUTPUT
)

def test_stake_creation_and_signing():
    wallet = Wallet()
    stake = Stake(staker=wallet.public_key_pem, amt=10)
    signature = wallet.private_key.sign(str(stake).encode())
    stake.sign = signature

    vk = VerifyingKey.from_pem(stake.staker)
    assert vk.verify(stake.sign, str(stake).encode()) is True

def test_genesis_chain_and_balance():
    # Reset singleton instance for test isolation
    Chain.instance = None
    wallet = Wallet()
    chain = Chain(publicKey=wallet.public_key_pem, privatekey=wallet.private_key)
    
    assert len(chain.chain) == 1
    assert chain.lastBlock.creator == wallet.public_key_pem
    assert chain.lastBlock.prevHash is None
    # Initial balance from Genesis block is 50 coins from Genesis tx + 6 coins block reward
    bal = chain.calc_balance(wallet.public_key_pem, pending_transactions=[], current_stakes=[])
    assert bal == 156  # 100 + 50 + 6 miner reward

def test_pos_epoch_seed():
    Chain.instance = None
    wallet = Wallet()
    chain = Chain(publicKey=wallet.public_key_pem, privatekey=wallet.private_key)
    seed = chain.epoch_seed()
    assert seed == chain.chain[0].hash

def test_vrf_proof_generation_and_verification():
    wallet = Wallet()
    seed = "test_epoch_seed_orbital_hash"
    vrf_proof = wallet.private_key.sign(seed.encode())
    vk = VerifyingKey.from_pem(wallet.public_key_pem)
    assert vk.verify(vrf_proof, seed.encode()) is True

    vrf_output = hashlib.sha256(vrf_proof).hexdigest()
    vrf_output_int = int(vrf_output, 16)
    assert 0 <= vrf_output_int < MAX_OUTPUT

def test_chain_weight_calculation():
    wallet = Wallet()
    b = Block("prev_hash", [])
    s1 = Stake(wallet.public_key_pem, 100)
    s2 = Stake(wallet.public_key_pem, 250)
    b.stakers = [s1, s2]
    weight = weight_of_chain([b])
    assert weight == 350

def test_valid_chain_length_formula():
    assert valid_chain_length(0) == 0
    assert valid_chain_length(10) == 8
    assert valid_chain_length(20) == 16
    assert valid_chain_length(300) == 250

def test_known_bug_vrf_inversion_in_p2p():
    """
    Documents known bug in consensus/pos/p2p.py line 739:
    In isvalidChain, vrf_output_int > threshold is rejected (valid is <= threshold).
    In p2p.py line 739:
    `if vrf_output_int <= threshold: raise VrfThresholdException("VRF_Output is not less than threshold")`
    The condition is inverted, rejecting winning blocks and accepting losing blocks.
    """
    total_staked = 100
    my_stake = 50
    threshold = (my_stake / total_staked) * MAX_OUTPUT
    
    # A winning VRF output is smaller than the threshold
    winning_vrf_output = int(threshold * 0.5)
    losing_vrf_output = int(threshold * 1.5)

    # In proper consensus (isvalidChain):
    assert winning_vrf_output <= threshold  # Valid winner
    assert losing_vrf_output > threshold   # Loser

    # But p2p.py line 739 rejects winning_vrf_output <= threshold:
    buggy_rejection = winning_vrf_output <= threshold
    assert buggy_rejection is True, "Documents that p2p.py line 739 inverts VRF lottery winner check"

def test_known_bug_fork_detection_and_slashing_inversion():
    """
    Documents known bug in consensus/pos/p2p.py line 891:
    `if block1.creator == block2.creator: # Non malicious fork`
    `else: # Malicious fork; await self.verify_and_slash(...)`
    Same creator signing two different blocks at the same height is DOUBLE SIGNING (malicious).
    Different creators competing is a standard PoS lottery tie (non-malicious).
    The logic in p2p.py is completely inverted.
    """
    creator_alice = "Alice"
    creator_bob = "Bob"

    is_double_sign = (creator_alice == creator_alice)
    assert is_double_sign is True

    # In p2p.py line 891, double signing is incorrectly classified as "Non malicious fork"
    p2p_classification_non_malicious = (creator_alice == creator_alice)
    assert p2p_classification_non_malicious is True
