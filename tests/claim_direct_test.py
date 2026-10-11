import json

PREMIUM = 10**16
FLIGHT_KEY = "LH430-20261015"
AIRLINE = "LH"
FLIGHT_NUMBER = "LH430"
DATE = "2026-10-15"

# GenVM release that matches the Studio (v0.2.16) and still publishes
# the genvm-universal.tar.xz file that Direct Mode downloads.
SDK_VERSION = "v0.2.16"

# Regex: matches the proxy URL the contract builds.
PROXY_PATTERN = r"flight-proxy-bice\.vercel\.app/api/flight-status"


def compact(obj):
    # Same formatting as the Vercel proxy's res.json(): no spaces.
    return json.dumps(obj, separators=(",", ":"))


def flight_record(status, arrival_delay):
    # Fake sample in the Aviationstack style (shape from memory).
    arrival = {"iata": "LOS", "scheduled": "2026-10-15T14:00:00+00:00"}
    if arrival_delay != "OMIT":
        arrival["delay"] = arrival_delay
    return {
        "flight_date": DATE,
        "flight_status": status,
        "departure": {
            "iata": "FRA",
            "scheduled": "2026-10-15T08:00:00+00:00",
        },
        "arrival": arrival,
        "airline": {"name": "Lufthansa", "iata": AIRLINE},
        "flight": {"number": "430", "iata": FLIGHT_NUMBER},
    }


def available(record):
    return compact({"status": "AVAILABLE", "data": [record]})


UNAVAILABLE_BODY = compact(
    {"status": "DATA_UNAVAILABLE", "reason": "No flight record was returned"}
)


def run_case(direct_vm, direct_deploy, alice, body, pays_out):
    contract = direct_deploy("contracts/FlightInsurance.py", sdk_version=SDK_VERSION)
    direct_vm.mock_web(PROXY_PATTERN, {"status": 200, "body": body})

    direct_vm.sender = alice
    direct_vm.value = PREMIUM
    contract.buy_policy(FLIGHT_KEY)
    direct_vm.value = 0

    if pays_out:
        # The mock does not credit the contract with the value sent in
        # buy_policy, so fund it directly: 5 premiums cover a 5 * 10**16 payout.
        direct_vm.deal(direct_vm._contract_address, 5 * PREMIUM)

    return contract.claim_payout(FLIGHT_KEY, AIRLINE, FLIGHT_NUMBER, DATE)


def test_missing_flight_data_is_unavailable(direct_vm, direct_deploy, direct_alice):
    result = run_case(direct_vm, direct_deploy, direct_alice, UNAVAILABLE_BODY, False)
    assert result == "DATA_UNAVAILABLE"


def test_on_time_flight_is_rejected(direct_vm, direct_deploy, direct_alice):
    body = available(flight_record("landed", 5))
    assert run_case(direct_vm, direct_deploy, direct_alice, body, False) == "CLAIM_REJECTED"


def test_delay_of_exactly_120_minutes_is_rejected(direct_vm, direct_deploy, direct_alice):
    body = available(flight_record("landed", 120))
    assert run_case(direct_vm, direct_deploy, direct_alice, body, False) == "CLAIM_REJECTED"


def test_delayed_flight_is_approved(direct_vm, direct_deploy, direct_alice):
    body = available(flight_record("landed", 190))
    assert run_case(direct_vm, direct_deploy, direct_alice, body, True) == "CLAIM_APPROVED"


def test_cancelled_flight_is_approved(direct_vm, direct_deploy, direct_alice):
    body = available(flight_record("cancelled", "OMIT"))
    assert run_case(direct_vm, direct_deploy, direct_alice, body, True) == "CLAIM_APPROVED"


def test_missing_delay_is_unavailable(direct_vm, direct_deploy, direct_alice):
    body = available(flight_record("landed", "OMIT"))
    assert run_case(direct_vm, direct_deploy, direct_alice, body, False) == "DATA_UNAVAILABLE"


def test_flight_not_yet_landed_is_unavailable(direct_vm, direct_deploy, direct_alice):
    body = available(flight_record("active", 200))
    assert run_case(direct_vm, direct_deploy, direct_alice, body, False) == "DATA_UNAVAILABLE"