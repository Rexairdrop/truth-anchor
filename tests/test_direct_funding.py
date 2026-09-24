import requests

def test_direct_sim_funding():
    address = "0xd73904E230057Ad5b00F1b9C902F6F1b356C412F"

    def rpc(method, params):
        response = requests.post(
            "http://127.0.0.1:4000/api",
            json={
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1,
            },
        )
        print(method, response.json())
        return response.json()

    rpc("sim_get_balance", [address])
    rpc("sim_fund_account", [address, 10**20])
    rpc("sim_get_balance", [address])
