import os
import shutil
import pytest
from storage.storage_manager import (
    save_key,
    load_key,
    save_chain,
    load_chain,
    save_peers,
    load_peers,
    get_consensus_dir
)

@pytest.fixture
def clean_test_storage():
    test_consensus = "test_pos"
    storage_dir = get_consensus_dir(test_consensus)
    yield test_consensus
    if os.path.exists(storage_dir):
        shutil.rmtree(storage_dir, ignore_errors=True)

def test_storage_key_save_and_load(clean_test_storage):
    test_consensus = clean_test_storage
    key_pem = "-----BEGIN EC PRIVATE KEY-----\nTEST_PEM_DATA\n-----END EC PRIVATE KEY-----"
    save_key(key_pem, test_consensus)
    loaded = load_key(test_consensus)
    assert loaded == key_pem

def test_storage_chain_save_and_load(clean_test_storage):
    test_consensus = clean_test_storage
    dummy_chain = [{"id": "block1", "transactions": []}]
    save_chain(dummy_chain, test_consensus)
    loaded = load_chain(test_consensus)
    assert loaded == dummy_chain

def test_storage_peers_save_and_load(clean_test_storage):
    test_consensus = clean_test_storage
    dummy_peers = {"127.0.0.1:5000": ["node1", "pubkey1"]}
    save_peers(dummy_peers, test_consensus)
    loaded = load_peers(test_consensus)
    assert loaded == dummy_peers
