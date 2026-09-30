import pytest
from smart_contract.contracts_db import SmartContractDatabase
from smart_contract.smart_contract import ContractEnvironment

def test_smart_contract_db():
    db = SmartContractDatabase()
    contract_id = "test_contract_42"
    code = "def contract_logic(arg, state):\n    return state, 'ok'"
    db.store_contract(contract_id, code)
    assert db.get_contract(contract_id) == code
    assert db.get_contract("non_existent") is None

def test_contract_execution():
    code = (
        "def increment(amount, state):\n"
        "    current = state.get('count', 0)\n"
        "    state['count'] = current + amount\n"
        "    return state, 'incremented'\n"
    )
    env = ContractEnvironment(code)
    state, msg, gas = env.run_contract("increment", [5], {})
    assert state == {"count": 5}
    assert msg == "incremented"
    assert gas > 0
