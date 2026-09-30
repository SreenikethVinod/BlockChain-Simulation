import sys

GAS_LIMIT = 10000

class GasMeter:
    """
    [SEC-09 Hardening] Deterministic execution line tracer and gas counter.
    Enforces maximum computational gas limits to prevent infinite loops and resource exhaustion.
    """
    def __init__(self, gas_limit: int = GAS_LIMIT):
        self.gas_used = 0
        self.gas_limit = gas_limit

    def tracer(self, frame, event, arg):
        if event == "line":
            self.gas_used += 1
            if self.gas_used > self.gas_limit:
                raise Exception("Out of gas")
        return self.tracer

    def start(self):
        sys.settrace(self.tracer)

    def stop(self):
        sys.settrace(None)
