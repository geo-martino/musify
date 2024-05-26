from pytest_mock import MockerFixture


def patch_input(values: list[str], mocker: MockerFixture) -> None:
    """``builtins.input`` calls will return the ``values`` in order, finishing on ''"""
    def input_return(*_, **__) -> str:
        """An order of return values for user input that will test various stages of the pause"""
        return values.pop(0) if values else ""

    mocker.patch("builtins.input", new=input_return)
