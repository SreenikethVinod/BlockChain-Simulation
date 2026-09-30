import json
import pytest
from shared_blockchain_structures import Transaction, Wallet, txs_to_json_digestable_form

def test_transaction_creation_and_serialization():
    wallet_alice = Wallet()
    wallet_bob = Wallet()
    tx = Transaction(payload=15, sender=wallet_alice.public_key_pem, receiver=wallet_bob.public_key_pem)
    
    assert tx.payload == 15
    assert tx.sender == wallet_alice.public_key_pem
    assert tx.receiver == wallet_bob.public_key_pem
    assert tx.id is not None
    assert tx.ts is not None

    d = tx.to_dict()
    assert d["payload"] == 15
    assert d["sender"] == wallet_alice.public_key_pem
    assert d["receiver"] == wallet_bob.public_key_pem
    assert d["id"] == tx.id

def test_transaction_valid_signature():
    wallet_alice = Wallet()
    wallet_bob = Wallet()
    tx = Transaction(payload=25, sender=wallet_alice.public_key_pem, receiver=wallet_bob.public_key_pem)
    signature = wallet_alice.private_key.sign(str(tx).encode())
    tx.sign = signature
    assert tx.is_valid_signature() is True

def test_transaction_tamper_detection():
    wallet_alice = Wallet()
    wallet_bob = Wallet()
    tx = Transaction(payload=25, sender=wallet_alice.public_key_pem, receiver=wallet_bob.public_key_pem)
    signature = wallet_alice.private_key.sign(str(tx).encode())
    tx.sign = signature

    # Tamper with payload
    tx.payload = 999
    assert tx.is_valid_signature() is False

def test_txs_to_json_digestable_form():
    wallet_alice = Wallet()
    wallet_bob = Wallet()
    tx = Transaction(payload=10, sender=wallet_alice.public_key_pem, receiver=wallet_bob.public_key_pem)
    tx.sign = wallet_alice.private_key.sign(str(tx).encode())
    digestable = txs_to_json_digestable_form([tx])
    assert len(digestable) == 1
    assert "sign" in digestable[0]
    assert digestable[0]["payload"] == 10
