PREMIUM = 10**16
FLIGHT_ID = "LH430-20261015"


def test_buy_policy(direct_vm, direct_deploy, direct_alice):
    # Set transaction context BEFORE deploying/loading the contract.
    direct_vm.sender = direct_alice
    direct_vm.value = PREMIUM

    contract = direct_deploy("contracts/FlightInsurance.py")

    contract.buy_policy(FLIGHT_ID)

    assert contract.get_policy_state(
        direct_alice,
        FLIGHT_ID
    ) == 0


def test_duplicate_policy_purchase_reverts(
    direct_vm,
    direct_deploy,
    direct_alice
):
    # Set transaction context BEFORE deploying/loading the contract.
    direct_vm.sender = direct_alice
    direct_vm.value = PREMIUM

    contract = direct_deploy("contracts/FlightInsurance.py")

    contract.buy_policy(FLIGHT_ID)

    with direct_vm.expect_revert():
        contract.buy_policy(FLIGHT_ID)