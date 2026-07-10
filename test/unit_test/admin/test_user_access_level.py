from unittest.mock import MagicMock, patch

import pytest

from api.common.exceptions import AdminException, UserNotFoundError
from api.db import AccessLevel
from admin.server.services import UserMgr


def test_update_user_access_level_success():
    user = MagicMock()
    user.id = "user-1"
    with patch("admin.server.services.UserService.query_user_by_email", return_value=[user]):
        with patch("admin.server.services.UserService.update_user") as update_user:
            msg = UserMgr.update_user_access_level("user@example.com", AccessLevel.KB_ONLY)
    assert msg == "access_level updated to kb_only"
    update_user.assert_called_once_with("user-1", {"access_level": AccessLevel.KB_ONLY})


def test_update_user_access_level_invalid_value():
    with pytest.raises(AdminException) as exc_info:
        UserMgr.update_user_access_level("user@example.com", "invalid")
    assert exc_info.value.code == 400
    assert "Invalid access_level" in exc_info.value.message


def test_update_user_access_level_user_not_found():
    with patch("admin.server.services.UserService.query_user_by_email", return_value=[]):
        with pytest.raises(UserNotFoundError):
            UserMgr.update_user_access_level("missing@example.com", AccessLevel.FULL)
