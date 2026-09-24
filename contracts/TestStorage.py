import genlayer as gl


class TestStorage(gl.contract.Contract):
    value: str

    def __init__(self):
        self.value = "hello"

    @gl.public.view
    def get_value(self) -> str:
        return self.value