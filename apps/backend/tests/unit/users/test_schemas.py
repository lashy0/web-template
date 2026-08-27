import pytest
from pydantic import ValidationError

from app.auth.roles import Role
from app.modules.users.schemas import CreateUserRequest, UpdateUserRequest


@pytest.mark.unit
@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        pytest.param(
            CreateUserRequest,
            {
                "name": "",
                "role": Role.OPERATOR,
                "login": "operator",
                "password": "correct-horse-battery-staple",
                "active": True,
            },
            id="create-name",
        ),
        pytest.param(UpdateUserRequest, {"name": ""}, id="update-name"),
        pytest.param(
            CreateUserRequest,
            {
                "name": "Operator",
                "role": Role.OPERATOR,
                "login": "Invalid login",
                "password": "correct-horse-battery-staple",
                "active": True,
            },
            id="create-login",
        ),
        pytest.param(UpdateUserRequest, {"login": "Invalid login"}, id="update-login"),
    ],
)
def test_create_and_update_apply_shared_user_field_constraints(
    schema: type[CreateUserRequest] | type[UpdateUserRequest],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)
