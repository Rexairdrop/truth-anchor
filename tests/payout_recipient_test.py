import time

import pytest

from gltest import get_contract_factory, get_default_account, get_gl_client
from gltest.assertions import tx_execution_succeeded

AMOUNT = 5 * 10**16


def wait_until(check, tries=40, delay=3):
    for _ in range(tries):
        if check():
            return True
        time.sleep(delay)
    return False


@pytest.mark.parametrize("method", ["pay_me", "pay_me_evm"])
def test_recipient_balance_around_payout(method):
    client = get_gl_client()
    account = get_default_account()

    client.fund_account(account.address, 10**20)

    factory = get_contract_factory("PayoutProbe")
    contract = factory.deploy(account=account)

    fund = contract.fund().transact(
        value=AMOUNT,
        wait_interval=2000,
        wait_retries=30,
    )
    assert tx_execution_succeeded(fund)
    wait_until(lambda: contract.get_balance().call() == AMOUNT)
    after_fund = client.get_balance(account.address)

    pay = getattr(contract, method)(args=[AMOUNT]).transact(
        wait_interval=2000,
        wait_retries=30,
    )
    assert tx_execution_succeeded(pay)

    wait_until(lambda: contract.get_balance().call() == 0)

    # Give the credit up to 90 seconds to show up on the account.
    arrived = wait_until(
        lambda: client.get_balance(account.address) > after_fund,
        tries=30,
        delay=3,
    )
    final = client.get_balance(account.address)

    print(
        "\n{}: account change = {}  ->  {}".format(
            method,
            final - after_fund,
            "DELIVERED" if arrived else "NOT delivered",
        )
    )