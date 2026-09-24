from gltest import get_default_account

def test_show_default():
    account = get_default_account()
    print("\nDEFAULT ACCOUNT:", account.address)