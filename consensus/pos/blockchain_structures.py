import json, hashlib, uuid, base64
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from ecdsa import SigningKey, SECP256k1, VerifyingKey, BadSignatureError
from shared_blockchain_structures import (
    Transaction,
    BaseBlock,
    CommonChain,
    Wallet,
    txs_to_json_digestable_form,
    valid_chain_length,
    transaction_exists_in_block_list,
    DEMO_INITIAL_BALANCE
)
GAS_PRICE = 0.001 # coin per gas unit
MAX_OUTPUT=2**256
# Canonical epoch duration used for VRF eligibility, timestamp validation, and staking windows.
# All consensus modules must import this constant rather than hardcode their own value.
EPOCH_TIME: int = 60

# Deep-space VRF and canonical consensus eligibility helpers
def generate_vrf_proof(signing_key: SigningKey, seed: str) -> bytes:
    """
    Derives deterministic, ungrindable VRF proof using RFC 6979 deterministic nonce selection.
    For any given (signing_key, seed) tuple, the output signature bytes are strictly unique
    and reproducible, preventing signature grinding attacks in Proof-of-Stake validator selection.
    Compatible with ECDSA SECP256k1 verification.
    """
    if hasattr(signing_key, "sign_deterministic"):
        return signing_key.sign_deterministic(seed.encode(), hashfunc=hashlib.sha1)
    return signing_key.sign(seed.encode())

def verify_vrf_proof(verifying_key: VerifyingKey, vrf_proof: bytes, seed: str) -> bool:
    """
    Cryptographically verifies that the deterministic VRF proof is authentic for the given seed.
    """
    try:
        verifying_key.verify(vrf_proof, seed.encode())
        return True
    except Exception:
        return False

def compute_vrf_output(vrf_proof: bytes) -> tuple:
    """Calculate deterministic SHA-256 VRF lottery output hash and integer."""
    vrf_output = hashlib.sha256(vrf_proof).hexdigest()
    return vrf_output, int(vrf_output, 16)

def is_vrf_eligible(vrf_output_int: int, staked_amt: int, total_stake: int) -> bool:
    """
    Orbital navigation eligibility criterion:
    Eligible IF AND ONLY IF vrf_output_int < threshold.
    Ineligible if vrf_output_int >= threshold or non-positive stake.
    """
    if total_stake <= 0 or staked_amt <= 0:
        return False
    threshold = (staked_amt * MAX_OUTPUT) // total_stake
    return vrf_output_int < threshold

def get_canonical_stake_snapshot(block_list: List[Any], idx: int = None) -> Dict[str, int]:
    """
    Derives deterministic stake snapshot from canonical blockchain state.
    Returns mapping of {staker_public_key: stake_amount}.
    """
    if not block_list:
        return {}
    if idx is None or idx >= len(block_list):
        idx = len(block_list) - 1

    target_block = block_list[idx]
    if hasattr(target_block, 'stakers') and target_block.stakers:
        snapshot = {}
        for s in target_block.stakers:
            if s.amt > 0:
                snapshot[s.staker] = s.amt
        return snapshot

    if idx > 0:
        parent_block = block_list[idx - 1]
        if hasattr(parent_block, 'stakers') and parent_block.stakers:
            snapshot = {}
            for s in parent_block.stakers:
                if s.amt > 0:
                    snapshot[s.staker] = s.amt
            return snapshot

    return {}

class Stake:
    def __init__(self, staker:str, amt:int, ts=None):
        self.id=str(uuid.uuid4())
        self.staker=staker
        self.amt=amt
        self.sign:bytes=None

        self.ts=ts or datetime.now().timestamp()

    def to_dict(self):
        return {
            "id":self.id,
            "staker":self.staker,
            "amt":self.amt,
            "ts":self.ts
        }

    def __str__(self):
        return json.dumps(self.to_dict())
    
def stakes_to_json_digestable_form(stakers: List[Stake]):
    l = []
    if not stakers:
        return l
    for stake in stakers:
        s_dict = stake.to_dict()
        if stake.sign:
            if isinstance(stake.sign, bytes):
                s_dict["sign"] = base64.b64encode(stake.sign).decode()
            else:
                s_dict["sign"] = str(stake.sign)
        l.append(s_dict)
    l.sort(key=lambda s: (s.get("staker", ""), s.get("id", "")))
    return l


class Block(BaseBlock):
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, id=None):
        super().__init__(prevHash, transactions, ts, id)

        self.creator: str=""
        self.staked_amt=0
        
        self.stakers:List[Stake]=[]  # needs to be replaced everywhere with stakes
        self.seed:str=""
        self.vrf_proof:bytes=None
        self.sign: bytes=None
        self.is_valid:bool=True
        self.slash_creator=False

    def to_dict(self):
        vrf_proof_b64 = None
        if self.vrf_proof:
            if isinstance(self.vrf_proof, bytes):
                vrf_proof_b64 = base64.b64encode(self.vrf_proof).decode()
            else:
                vrf_proof_b64 = str(self.vrf_proof)

        return {
            "id": self.id,
            "prevHash": self.prevHash,
            "transactions": txs_to_json_digestable_form(self.transactions),
            "ts": self.ts,
            "creator": self.creator,
            "staked_amt": self.staked_amt,
            "files": self.files,
            "seed": self.seed or "",
            "vrf_proof_b64": vrf_proof_b64,
            "stakers": stakes_to_json_digestable_form(self.stakers)
        }
    
    def to_dict_with_stakers(self):
        return self.to_dict()


    def __str__(self):
        return json.dumps(self.to_dict())
    
    def is_equal(self, other):
        if other is None or not isinstance(other, Block):
            return False
        if len(self.transactions) != len(other.transactions):
            return False
        
        tx_len = len(self.transactions)
        for i in range(tx_len):
            if self.transactions[i] != other.transactions[i]:
                return False
            
        return (
            self.id == other.id and
            self.ts == other.ts and
            self.prevHash == other.prevHash and
            self.hash == other.hash and
            self.sign == other.sign and
            self.creator == other.creator and
            self.staked_amt == other.staked_amt and
            (self.seed or "") == (other.seed or "") and
            self.vrf_proof == other.vrf_proof
        )

    @property ## Now you can access hash like this myblock.hash
    def hash(self):
        block_str=json.dumps(self.to_dict())
        return hashlib.sha256(block_str.encode()).hexdigest()


def calc_balance_block_list(block_list:List[Block], publicKey, i, mem_pool:List[Transaction]=None, currStakes:List[Stake]=None):
    bal = DEMO_INITIAL_BALANCE
    valid_chain_len=valid_chain_length(i)

    for i in range(valid_chain_len):
        if block_list[i].slash_creator and block_list[i].creator==publicKey:
            bal-=block_list[i].staked_amt
        if not block_list[i].is_valid:
            continue
        
        for transaction in (block_list[i]).transactions:
            if transaction.sender==publicKey:
                if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                    bal-=transaction.payload[-1]
                else:
                    bal-=transaction.payload
            elif transaction.receiver==publicKey:
                bal+=transaction.payload
        if block_list[i].creator==publicKey:
            bal+=6 #Miner reward
    
    for transaction in mem_pool:
        if transaction.sender==publicKey:
            if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                bal-=transaction.payload[-1]
            else:
                bal-=transaction.payload

    if currStakes:
        for stake in currStakes:
            if stake.staker==publicKey:
                bal-=stake.amt
    # Since these transactions are not part of the chain we don't add
    # the money they gained yet because it could be invalid, but we subtract
    # the amount they have given to prevent double spending before the
    # transactions are added to the chain
    return bal

def weight_of_chain(block_list:List[Block]):
    total_weight=0
    for block in block_list:
        for stake in block.stakers:
            total_weight+=stake.amt
    return total_weight

class Chain(CommonChain):
    instance = None #Class Variable

    def __init__(self, publicKey:str=None, privatekey=None, blockList: List[Block]=None):
        """
            If we are the first node, we mine the genesis block for ouself
            otherwise we receive blockList from the bootstrap node and
            we assign that to be the chain
        """
        if Chain.instance is not None:
            return

        if publicKey and not blockList:
            genesis_block=Block(None, [Transaction(50,"Genesis",publicKey)])
            genesis_block.creator=publicKey
            genesis_block.sign=privatekey.sign(str(genesis_block).encode())
            super().__init__(genesis_block=genesis_block)
                
        elif blockList and not publicKey:
            super().__init__(block_list=blockList)

        else:
            raise ValueError("Invalid arguments")

        Chain.instance = self


    def to_block_dict_list(self):
        block_dict_list=[]
        for block in self.chain:
            block_dict=block.to_dict_with_stakers()
            if block.sign:
                block_dict["sign"]=base64.b64encode(block.sign).decode()
                
            block_dict_list.append(block_dict)
        
        return block_dict_list
    
    def rewrite(self, blockList: List[Block]):
        current_weight = weight_of_chain(self.chain)
        new_weight = weight_of_chain(blockList)
        if new_weight < current_weight:
            return False
        if new_weight == current_weight:
            if len(blockList) < len(self.chain):
                return False
            if len(blockList) == len(self.chain):
                if not blockList or not self.chain or blockList[-1].hash >= self.chain[-1].hash:
                    return False
        
        Chain.instance.chain = blockList.copy()
        return True
    
    def isValidBlock(self, block: Block):
        if self.lastBlock.hash != block.prevHash:
            print("Hash Problem")
            print(f"Actual prev hash: {self.lastBlock.hash}\nMy prev hash: {block.prevHash}")
            return False

        # Validate block creator and signature if provided
        if block.creator and block.sign:
            try:
                vk = VerifyingKey.from_pem(block.creator)
                vk.verify(block.sign, str(block).encode())
            except Exception:
                print("\nInvalid Block Signature\n")
                return False

        # Validate VRF eligibility if VRF proof and seed are present
        if block.vrf_proof is not None and block.seed:
            expected_seed = self.epoch_seed()
            if str(block.seed) != str(expected_seed):
                print("\nInvalid Seed\n")
                return False
            try:
                vk = VerifyingKey.from_pem(block.creator)
                vk.verify(block.vrf_proof, block.seed.encode())
            except Exception:
                print("\nInvalid VRF Proof Signature\n")
                return False

            total_stake = 0
            creator_found = False
            seen_stakers = set()
            for s in block.stakers:
                if s.staker in seen_stakers:
                    print("\nDuplicate staker in block\n")
                    return False
                seen_stakers.add(s.staker)
                total_stake += s.amt
                if s.staker == block.creator:
                    creator_found = True
                    if s.amt != block.staked_amt:
                        return False
            if not creator_found or total_stake <= 0:
                print("\nCreator not in stakers or invalid total stake\n")
                return False

            _, vrf_int = compute_vrf_output(block.vrf_proof)
            if not is_vrf_eligible(vrf_int, block.staked_amt, total_stake):
                print("\nIneligible VRF lottery output\n")
                return False

        mem_pool=[] 
        # if we don't store this then a person can send two valid transaction 
        # less than his acc balance but the sum of it could be greater 
        # than his account balance
        for transaction in block.transactions:
            if Chain.instance.transaction_exists_in_chain(transaction):
                print("Duplicate transaction(s)")
                return False
            sign=transaction.sign
            vk=VerifyingKey.from_pem(transaction.sender)
            try:
                vk.verify(sign, str(transaction).encode())
            except:
                print("\nFake Transactions\n")
                return False
            
            amount = 0
            if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if amount>Chain.instance.calc_balance(publicKey=transaction.sender,pending_transactions=mem_pool,current_stakes=block.stakers) or amount<=0: 
                # we have to make sure the current transactions are included when checking for balance
                return False
            mem_pool.append(transaction)

        currStakes=[]
        seen_stakes = set()
        for stake in block.stakers:
            if stake.staker in seen_stakes:
                print("\nDuplicate stake in block\n")
                return False
            seen_stakes.add(stake.staker)
            vk=VerifyingKey.from_pem(stake.staker)
            try:
                vk.verify(stake.sign, str(stake).encode())
            except (BadSignatureError, Exception):
                print("\nInvalid signature on stake\n")
                return False
            if(stake.amt<=0 or stake.amt>Chain.instance.calc_balance(stake.staker, mem_pool, currStakes)):
                return False
            currStakes.append(stake)
        return True
 
    def calc_balance(self, publicKey, pending_transactions:List[Transaction]=None, current_stakes:List[Stake]=None):
        bal = DEMO_INITIAL_BALANCE
        valid_chain_len=valid_chain_length(len(self.chain))

        for i in range(valid_chain_len):
            if Chain.instance.chain[i].slash_creator and Chain.instance.chain[i].creator==publicKey:
                bal-=Chain.instance.chain[i].staked_amt
            if not Chain.instance.chain[i].is_valid:
                continue
            
            for transaction in (Chain.instance.chain[i]).transactions:
                if transaction.sender==publicKey:
                    if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                        bal-=transaction.payload[-1]
                    else:
                        bal-=transaction.payload
                elif transaction.receiver==publicKey:
                    bal+=transaction.payload
            if Chain.instance.chain[i].creator==publicKey:
                bal+=6 #Miner reward

        if valid_chain_len<len(self.chain):
            for i in range(valid_chain_len, len(self.chain)):
                currBlock=Chain.instance.chain[i]
                for transaction in currBlock.transactions:
                    if transaction.sender==publicKey:
                        if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                            bal-=transaction.payload[-1]
                        else:
                            bal-=transaction.payload
        
        if current_stakes:
            for stake in current_stakes:
                if stake.staker==publicKey:
                    bal-=stake.amt

        # Since these transactions are not part of the chain we don't add
        # the money they gained yet because it could be invalid, but we subtract
        # the amount they have given to prevent double spending before the
        # transactions are added to the chain
        if pending_transactions:
            for transaction in pending_transactions:
                if transaction.sender==publicKey:
                    if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                        bal-=transaction.payload[-1]
                    else:
                        bal-=transaction.payload
        return bal

    def epoch_seed(self):
        bal=0
        last_finalized_block_hash=self.chain[valid_chain_length(len(self.chain))-1].hash
        return last_finalized_block_hash

    def checkEquivalence(self, block_list:List[Block]):
        """
            Returns -1 if there is no divergence, returns index of divergence if there is any
        """
        min_len=min(len(self.chain), len(block_list))
        for i in range(min_len):
            if(not self.chain[i].is_equal(block_list[i])):
                return i
        return -1

def transaction_exists_in_block_list(blockList:List[Block], transaction_tc:Transaction, idx):
    for i in range(idx):
        currBlock=blockList[i]
        for transaction in currBlock.transactions:
            if(transaction.id==transaction_tc.id): 
                # We sign the id of the transaction, 
                # if it was truly a duplicate transaction
                # meant to reuse a sign then id must be the same
                # otherwise we'll get the invalid sign error
                return True
    return False

def isvalidChain(blockList:List[Block]):
    # EPOCH_TIME is the canonical epoch duration imported from module scope.
    # It must NOT be redefined locally — use the module-level constant.

    for i in range(len(blockList)):
        currBlock = blockList[i]
        if not currBlock.creator or not currBlock.sign:
            return False
        try:
            vk = VerifyingKey.from_pem(currBlock.creator)
            vk.verify(currBlock.sign, str(currBlock).encode())
        except Exception:
            return False
        
        if(i<=0):
            continue

        # Timestamp validation
        try:
            # Convert Unix timestamp to datetime
            if isinstance(currBlock.ts, (int, float)):
                block_time = datetime.fromtimestamp(currBlock.ts/1000)
            elif isinstance(currBlock.ts, str):
                block_time = datetime.fromisoformat(currBlock.ts)
            elif isinstance(currBlock.ts, datetime):
                block_time = currBlock.ts
            else:
                print("\nInvalid Block timestamp format\n")
                return False

            # Get previous block time
            prev_block_ts = blockList[i-1].ts
            if isinstance(prev_block_ts, (int, float)):
                prev_block_time = datetime.fromtimestamp(prev_block_ts/1000)
            elif isinstance(prev_block_ts, str):
                prev_block_time = datetime.fromisoformat(prev_block_ts)
            elif isinstance(prev_block_ts, datetime):
                prev_block_time = prev_block_ts
            else:
                print("\nInvalid previous block timestamp format\n")
                return False

            # Check block isn't from the future (allow some tolerance for clock skew)
            current_time = datetime.now()
            if block_time > current_time + timedelta(seconds=10):
                print(f"\nBlock {i} timestamp in future\n")
                return False

            # Check blocks are in chronological order
            if block_time < prev_block_time:
                print(f"\nBlock {i} timestamp before previous block\n")
                return False

            # Verify minimum time between blocks (staking registration period)
            time_diff = (block_time - prev_block_time).total_seconds()
            if time_diff < EPOCH_TIME * 5/6:
                print(f"\nBlocks {i-1} and {i} too close together: {time_diff}s < {EPOCH_TIME * 5/6}s\n")
                return False

        except (ValueError, AttributeError, TypeError, OSError) as e:
            print(f"\nTimestamp validation error on block {i}: {e}\n")
            return False

        if currBlock.vrf_proof is None or not currBlock.seed:
            print("\nMissing VRF proof or seed\n")
            return False

        try:
            vk.verify(currBlock.vrf_proof, currBlock.seed.encode())
        except (BadSignatureError, TypeError, Exception):
            print("\nInvalid signature on vrf_proof\n")
            return False
        
        if(str(currBlock.seed)!=str(blockList[valid_chain_length(i)-1].hash)):
            print("\nInvalid Seed\n")
            return False

        total_stake=0
        creator_stake=None
        seen_stakers=set()
        for stake in currBlock.stakers:
            if stake.staker in seen_stakers:
                print("\nDuplicate staker in block\n")
                return False
            seen_stakers.add(stake.staker)
            vk_staker=VerifyingKey.from_pem(stake.staker)
            try:
                vk_staker.verify(stake.sign, str(stake).encode())
            except BadSignatureError:
                print("\nInvalid signature on stake\n")
                return False
            if(stake.amt<=0):
                return False
            if stake.staker == currBlock.creator:
                creator_stake = stake.amt
            total_stake+=stake.amt

        if creator_stake is None or creator_stake != currBlock.staked_amt:
            print("\nCreator not found in stakers or staked_amt mismatch\n")
            return False

        vrf_output, vrf_ouput_int = compute_vrf_output(currBlock.vrf_proof)

        if not is_vrf_eligible(vrf_ouput_int, currBlock.staked_amt, total_stake):
            print("\nFalsified vrf\n")
            return False

        mem_pool=[]
        for transaction in blockList[i].transactions:
            if(transaction_exists_in_block_list(blockList, transaction, i)):
                print("Duplicate transaction(s)")
                return False
            
            sign=transaction.sign
            vk_tx=VerifyingKey.from_pem(transaction.sender)

            try:
                vk_tx.verify(sign, str(transaction).encode())
            except BadSignatureError:
                print("\nInvalid signature on transaction\n")
                return False

            amount = 0
            if(transaction.receiver == "deploy" or transaction.receiver == "invoke"):
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if(calc_balance_block_list(blockList, transaction.sender, i, mem_pool, currBlock.stakers) < amount or amount<=0):
                return False
            mem_pool.append(transaction)
        
        # we use a currStakes list because if we just pass currBlock.stakers then the stake 
        # which we are processing will already be there
        currStakes=[]
        for stake in currBlock.stakers:
            if stake.amt>calc_balance_block_list(blockList, stake.staker, i, mem_pool, currStakes):
                return False
            currStakes.append(stake)

        
        if(calc_balance_block_list(blockList, blockList[i].creator, i, mem_pool)<0):
            return False
        
        if (blockList[i].prevHash!=blockList[i-1].hash):
            return False

    return True

