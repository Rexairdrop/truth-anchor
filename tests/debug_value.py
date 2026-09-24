def test_value_sync(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/FlightInsurance.py")

    direct_vm.sender = direct_alice
    direct_vm.value = 10**16

    print("VM VALUE:", direct_vm.value)

    # Ask the contract itself what gl.message.value sees.
    value = contract.get_message_value()

    print("CONTRACT MESSAGE VALUE:", value)

    assert direct_vm.value == 10**16
    assert int(value) == 10**16