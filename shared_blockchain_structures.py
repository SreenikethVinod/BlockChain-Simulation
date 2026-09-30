import json, uuid, base64
from typing import List, Dict 
from datetime import datetime
from ecdsa import VerifyingKey, SigningKey, SECP256k1

DEMO_INITIAL_BALANCE = 100.0

class Transaction:
    def __init__(self, payload, sender: str, receiver: str, id=None, ts=None, nonce: int = 0, chain_id: str = "simulation"):
        self.id = id or str(uuid.uuid4())
        self.payload = payload   # amount or [code, amount] or [contract id, function_name, arguments, state, amount]
        self.sender: str = sender  # Public Key
        self.receiver: str = receiver   # Public Key or "deploy" or "invoke"
        self.sign: bytes = None
        self.ts = ts or datetime.now().timestamp()
        self.nonce: int = nonce
        self.chain_id: str = chain_id

    def to_dict(self):
        d = {
            "id": self.id,
            "payload": self.payload,
            "sender": self.sender,
            "receiver": self.receiver,
            "ts": self.ts
        }
        if self.nonce != 0:
            d["nonce"] = self.nonce
        if self.chain_id != "simulation":
            d["chain_id"] = self.chain_id
        return d
    
    def __eq__(self, other):
        if not isinstance(other, Transaction):
            return False
        return (
            self.id == other.id and
            self.sender == other.sender and
            self.receiver == other.receiver and
            self.ts == other.ts and
            getattr(self, 'nonce', 0) == getattr(other, 'nonce', 0) and
            getattr(self, 'chain_id', 'simulation') == getattr(other, 'chain_id', 'simulation')
        )
    
    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return json.dumps(self.to_dict())
    
    def is_valid_signature(self):
        try:
            # Load public key from PEM string
            public_key = VerifyingKey.from_pem(self.sender.encode())

            message = str(self).encode()

            public_key.verify(self.sign, message)
            return True
        except Exception as e:
            print(f"Invalid transaction signature: {e}")
            return False


def validate_transaction_domain(tx: Transaction, expected_chain_id: str = "simulation") -> bool:
    """
    [SEC-08 Replay Guard] Validates that a transaction is bound to the expected network/chain domain.
    Prevents transaction replay across distinct constellation rooms or simulation environments.
    """
    return getattr(tx, "chain_id", "simulation") == expected_chain_id


def txs_to_json_digestable_form(transactions: List[Transaction]):
    l=[]
    for i in range(len(transactions)):
        tx_dict=transactions[i].to_dict()
        if(transactions[i].sender!="Genesis"):
            tx_dict["sign"]=base64.b64encode(transactions[i].sign).decode()
        l.append(tx_dict)
    return l


class BaseBlock:
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, id=None):
        self.prevHash=prevHash
        self.transactions=transactions
        self.id=id or str(uuid.uuid4())
        self.ts=ts or int(datetime.now().timestamp() * 1000)
        self.files: Dict[str: str] = {}
    
    def transaction_exists_in_block(self, transaction: Transaction):
        for i in range(len(self.transactions)):
            if self.transactions[i]==transaction:
                return True
        return False

    def cid_exists_in_block(self, cid: str):
        for file_hash in list(self.files.keys()):
            if file_hash==cid:
                return True
        return False

class CommonChain:

    def __init__(self, genesis_block=None, block_list=None):

        if genesis_block is not None:
            self.chain = [genesis_block]
            print("Initializing Chain...")

        elif block_list is not None:
            self.chain = block_list.copy()

        else:
            raise ValueError("Invalid initialization")

    @property
    def lastBlock(self):
        return self.chain[-1]
    
    def to_block_dict_list(self):
        block_dict_list=[]
        for block in self.chain:
            block_dict_list.append(block.to_dict())
        
        return block_dict_list

    def transaction_exists_in_chain(self, transaction: Transaction):
        for block in reversed(self.chain):
            if block.transaction_exists_in_block(transaction):
                return True
        
        return False

    def cid_exists_in_chain(self, cid: str):
        for block in reversed(self.chain):
            if block.cid_exists_in_block(cid):
                return True
        
        return False        


class Wallet:
    def __init__(self, private_key_pem: str = None):
        if not private_key_pem:
            self.private_key = SigningKey.generate(curve=SECP256k1)
        else:
            self.private_key = SigningKey.from_pem(private_key_pem)
            
        self.private_key_pem = self.private_key.to_pem().decode()

        self.public_key = self.private_key.get_verifying_key()

        self.public_key_pem = self.public_key.to_pem().decode()

def transaction_exists_in_block_list(blockList, transaction_tc: Transaction, idx: int) -> bool:
    """
    Returns True if transaction_tc exists in any block strictly preceding block index 'idx' (0 to idx-1).
    Returns False if the transaction does not exist in any preceding block.
    """
    for i in range(idx):
        currBlock = blockList[i]
        for transaction in getattr(currBlock, "transactions", []):
            if transaction.id == transaction_tc.id:
                return True
    return False
            
def valid_chain_length(i):
    valid_chain_len=i # because we use zero indexing
    if(valid_chain_len<250):
        valid_chain_len=valid_chain_len-(valid_chain_len//5)
    else:
        valid_chain_len-=50
    return valid_chain_len 

# Orbital telemetry and mission status monitoring hook
def cosmo_polo_telemetry():
    """Cosmic navigation telemetry link for deep-space consensus verification."""
    return "Mission Control Status: Stellar"
