import json

import pytest

PREMIUM = 10**16
FLIGHT_KEY = "LH430-20261015"
AIRLINE = "LH"
FLIGHT_NUMBER = "LH430"
DATE = "2026-10-15"
SDK_VERSION = "v0.2.16"

PROXY_PATTERN = r"flight-proxy-bice\.vercel\.app/api/flight-status"

DELAYED_BODY = json.dumps(
    {
        "status": "AVAILABLE",
        "data": [
            {
                "flight_status": "landed",
                "arrival": {
                    "scheduled": "2026-10-15T14:00:00+00:00",
                    "delay": 190,
                },
            }
        ],
    },
    separators=(",", ":"),
)


def buy(contract, vm, who, amount=PREMIUM):
    vm.sender = who
    vm.value = amount
    contract.buy_policy(FLIGHT_KEY)
    vm.value = 0


def claim(contract, vm, who):
    vm.sender = who
    vm.value = 0
    return contract.claim_payout(FLIGHT_KEY, AIRLINE, FLIGHT_NUMBER, DATE)


def test_second_buyer_cannot_reopen_a_paid_claim(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/FlightInsurance.py", sdk_version=SDK_VERSION)
    direct_vm.mock_web(PROXY_PATTERN, {"status": 200, "body": DELAYED_BODY})

    # Enough balance in the contract for two payouts.
    direct_vm.deal(direct_vm._contract_address, 10 * PREMIUM)

    # Alice buys and is paid once.
    buy(contract, direct_vm, direct_alice)
    assert claim(contract, direct_vm, direct_alice) == "CLAIM_APPROVED"

    # Bob buys the same flight afterwards.
    buy(contract, direct_vm, direct_bob)

    # Alice must NOT be able to claim again.
    with pytest.raises(Exception) as err:
        claim(contract, direct_vm, direct_alice)

    assert "already been processed" in f"{err.value!r} {err.value}"


def test_each_buyer_has_an_independent_status(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/FlightInsurance.py", sdk_version=SDK_VERSION)
    direct_vm.mock_web(PROXY_PATTERN, {"status": 200, "body": DELAYED_BODY})
    direct_vm.deal(direct_vm._contract_address, 10 * PREMIUM)

    buy(contract, direct_vm, direct_alice)
    buy(contract, direct_vm, direct_bob)

    # Both can be paid exactly once.
    assert claim(contract, direct_vm, direct_alice) == "CLAIM_APPROVED"
    assert claim(contract, direct_vm, direct_bob) == "CLAIM_APPROVED"