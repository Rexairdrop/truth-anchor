from gltest import get_gl_client, get_default_account

def test_check_funding():
    client = get_gl_client()
    account = get_default_account()

    balance = client.get_balance(account.address)

    print("")
    print("ACCOUNT:", account.address)
    print("BALANCE:", balance)

    assert balance == 10**20
