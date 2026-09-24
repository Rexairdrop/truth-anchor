from pathlib import Path

from gltest.direct.sdk_loader import setup_sdk_paths
from gltest.direct.sdk_compat import import_calldata, import_address

contract_path = Path("contracts/FlightInsurance.py").resolve()

print("Setting up SDK paths...")
setup_sdk_paths(contract_path, None)

print("Importing calldata...")
calldata = import_calldata()
Address = import_address()

print("calldata:", calldata)
print("Address:", Address)

message_data = {
    "contract_address": Address(b"\x11" * 20),
    "sender_address": Address(b"\x22" * 20),
    "origin_address": None,
    "stack": [],
    "value": 0,
    "datetime": 0,
    "is_init": False,
    "chain_id": 0,
    "entry_kind": 0,
    "entry_data": b"",
    "entry_stage_data": None,
}

print("Encoding message...")
encoded = calldata.encode(message_data)

print("Encoded type:", type(encoded))
print("Encoded length:", len(encoded))
print("Encoded bytes:", encoded[:100])

print("Decoding message...")
decoded = calldata.decode(encoded)

print("Decoded successfully:")
print(decoded)