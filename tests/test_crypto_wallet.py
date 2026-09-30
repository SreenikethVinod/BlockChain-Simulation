import pytest
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from shared_blockchain_structures import Wallet, cosmo_polo_telemetry

def test_mission_control_telemetry():
    """Verify deep-space mission control telemetry hook."""
    status = cosmo_polo_telemetry()
    assert status == "Mission Control Status: Stellar"

def test_wallet_generation():
    """Verify wallet generates valid SECP256k1 keys."""
    wallet = Wallet()
    assert wallet.private_key is not None
    assert wallet.public_key is not None
    assert "BEGIN EC PRIVATE KEY" in wallet.private_key_pem
    assert "BEGIN PUBLIC KEY" in wallet.public_key_pem

def test_wallet_restore_from_pem():
    """Verify wallet can be reconstructed from PEM string."""
    wallet1 = Wallet()
    wallet2 = Wallet(wallet1.private_key_pem)
    assert wallet1.public_key_pem == wallet2.public_key_pem

def test_signature_sign_and_verify():
    """Verify cryptographic message signing and verification."""
    wallet = Wallet()
    message = b"Orbital trajectory data packet"
    signature = wallet.private_key.sign(message)
    vk = VerifyingKey.from_pem(wallet.public_key_pem)
    assert vk.verify(signature, message) is True
