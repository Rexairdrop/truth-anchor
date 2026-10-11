from gltest import get_contract_factory, get_default_account
from gltest.assertions import tx_execution_succeeded


PREMIUM = 10**16
FLIGHT_KEY = "LH430-20261015"


def test_buy_policy():
    factory = get_contract_factory("FlightInsurance")

    account = get_default_account()

    contract = factory.deploy(account=account)

    tx = contract.buy_policy(args=[FLIGHT_KEY]).transact(
        value=PREMIUM,
        wait_interval=2000,
        wait_retries=30,
    )

    assert tx_execution_succeeded(tx)

    state = contract.get_policy_state(
        args=[account.address, FLIGHT_KEY]
    ).call()

    assert state == 0


def test_duplicate_policy_purchase_reverts():
    factory = get_contract_factory("FlightInsurance")

    account = get_default_account()

    contract = factory.deploy(account=account)

    first_tx = contract.buy_policy(args=[FLIGHT_KEY]).transact(
        value=PREMIUM,
        wait_interval=2000,
        wait_retries=30,
    )

    assert tx_execution_succeeded(first_tx)

    second_tx = contract.buy_policy(args=[FLIGHT_KEY]).transact(
        value=PREMIUM,
        wait_interval=2000,
        wait_retries=30,
    )

    assert not tx_execution_succeeded(second_tx)