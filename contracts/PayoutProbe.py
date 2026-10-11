# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass

    class Write:
        pass


class PayoutProbe(gl.Contract):
    def __init__(self):
        pass

    @gl.public.write.payable
    def fund(self) -> None:
        """Accept value so the contract has a balance to pay from."""
        pass

    @gl.public.write
    def pay_me(self, amount: int) -> None:
        """Send `amount` back to the caller with the plain GenVM transfer."""
        value = u256(amount)

        if self.balance < value:
            raise gl.vm.UserError("Insufficient contract balance.")

        gl.get_contract_at(gl.message.sender_address).emit_transfer(
            value=value
        )

    @gl.public.write
    def pay_me_evm(self, amount: int) -> None:
        """Send `amount` back to the caller through the EVM interface."""
        value = u256(amount)

        if self.balance < value:
            raise gl.vm.UserError("Insufficient contract balance.")

        _Recipient(gl.message.sender_address).emit_transfer(value=value)

    @gl.public.view
    def get_balance(self) -> int:
        return int(self.balance)