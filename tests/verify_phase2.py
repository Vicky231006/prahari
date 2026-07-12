"""Quick verification that all generators import and produce valid events."""
import sys
import json
sys.path.insert(0, ".")

from data.synthetic.generators.base import (
    IdentityState, lognormal_amount, IDENTITY_POOL, GEO_POOL,
    LEGACY_KEY_EXCHANGES, PQC_KEY_EXCHANGES
)

# Test identity state
s = IdentityState("ID-00001")
print(f"Identity: {s.identity_id}")
print(f"Home geo: {s.home_geo['city']}")
print(f"Devices: {len(s.known_devices)}")
print(f"Beneficiaries: {len(s.known_beneficiaries)}")
print(f"Sample txn amount: {lognormal_amount()}")
print(f"Identity pool size: {len(IDENTITY_POOL)}")

# Test security telemetry gen
from data.synthetic.generators.security_telemetry_gen import generate_normal_security_event
evt = generate_normal_security_event(s)
print(f"\nSecurity event: type={evt['event_type']}, ip={evt['source_ip']}, flags={evt['risk_flags']}")
assert evt["identity_id"] == "ID-00001"
assert evt["risk_flags"] == []
assert evt["is_new_device"] == False

# Test transaction gen
from data.synthetic.generators.transaction_gen import generate_normal_transaction
txn = generate_normal_transaction(s)
print(f"Transaction: channel={txn['channel']}, amount={txn['amount']}, currency={txn['currency']}")
assert txn["currency"] == "INR"
assert txn["beneficiary_is_new"] == False
assert txn["amount"] > 0

# Test TLS gen
from data.synthetic.generators.tls_handshake_gen import generate_normal_tls_event
tls = generate_normal_tls_event()
print(f"TLS: kx={tls['key_exchange']}, sig={tls['signature_algo']}, sensitivity={tls['data_sensitivity']}")
assert tls["key_exchange"] in LEGACY_KEY_EXCHANGES + PQC_KEY_EXCHANGES

# Test scenario injector imports
from data.synthetic.generators.scenario_injector import (
    inject_ato_scenario,
    inject_insider_collusion_scenario,
    inject_credential_stuffing_ato_scenario,
    inject_hndl_exposure_scenario,
)
print("\nAll four scenario injectors imported successfully")

# Test run_generators import
from data.synthetic.generators.run_generators import main
print("run_generators.main imported successfully")

print("\n" + "=" * 50)
print("PHASE 2 VERIFICATION: ALL GENERATORS PASS")
print("=" * 50)
