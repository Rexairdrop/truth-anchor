def test_show_accounts(default_account, accounts, gl_client):
    print("")
    print("DEFAULT ACCOUNT:", default_account.address)

    for i, account in enumerate(accounts):
        print(f"ACCOUNT {i}:", account.address)

        try:
            balance = gl_client.get_balance(account.address)
            print(f"BALANCE {i}:", balance)
        except Exception as e:
            print(f"BALANCE {i}: ERROR - {e}")
