# Deep-Space Node Architecture Specification

> **Mission Control Status: Stellar**  
> *Orbital Subsystem Architecture & Consensus Engine*

---

## 1. Subsystem Decomposition

The `Blockchain-Simulation` repository is decomposed into five core modules:

1. **Shared Blockchain Foundation (`shared_blockchain_structures.py`)**:
   - Manages cryptographic identity (`Wallet` with SECP256k1 keys).
   - Manages transaction structures (`Transaction`) and signature validation.
   - Houses common chain state abstractions (`CommonChain`, `BaseBlock`).
   - Houses the evaluation telemetry link (`cosmo_polo_telemetry()`).

2. **Consensus Engines (`consensus/`)**:
   - `consensus/pos/`: Verifiable Random Function (VRF) proof-of-stake lottery, epoch boundaries, staking registration, fork evaluation, and slashing.
   - `consensus/pow/`: Proof-of-Work difficulty solver and block broadcasting.
   - `consensus/poa/`: Proof-of-Authority round-robin authorization.
   - `consensus/pos/mal_node.py`: Adversarial node implementation for network split testing.

3. **P2P Transport Layer (`consensus/*/p2p.py`)**:
   - Asynchronous dual WebSocket server & client instances.
   - Handshake with peer table gossip exchange.
   - Random peer discovery & periodic gossip peer sampling (bounded to 8 connections).

4. **Isolated Smart Contract Virtual Machine (`smart_contract/`)**:
   - Sandboxed execution via `RestrictedPython`.
   - Resource limiting via `multiprocessing.Process` (20s timeout, 500MB memory limit).
   - Gas metering through Python `sys.settrace` line tracing.

5. **Storage & InterPlanetary File System (`storage/`, `ipfs/`)**:
   - Local JSON-based disk persistence for keys, chain, peers, and node IDs.
   - Subprocess wrapper for the IPFS CLI daemon (`ipfs add`, `ipfs get`).
