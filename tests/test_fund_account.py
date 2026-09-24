from gltest import get_gl_client, get_default_account

def test_fund_default_account():
    client = get_gl_client()
    account = get_default_account()

    print("")
    print("ACCOUNT:", account.address)

    before = client.get_balance(account.address)
    print("BEFORE:", before)

    client.fund_account(account.address, 10**20)

    after = client.get_balance(account.address)
    print("AFTER:", after)

    assert after > before
