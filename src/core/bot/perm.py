from enum import IntEnum

from src.core.constants import Constants


class PermissionLevel(IntEnum):
    """会话权限控制"""
    USER = 0
    MOD = 1
    ADMIN = 2

    def is_admin(self):
        return self.value >= self.ADMIN

    def is_mod(self):
        return self.value >= self.MOD

    def is_user(self):
        return self.value >= self.USER

    @staticmethod
    def distribute_permission(qq_id: str):
        admin_ids = Constants.role_conf.get('admin_id', set())
        mod_ids = Constants.role_conf.get('mod_id', set())
        return (
            PermissionLevel.ADMIN if qq_id in admin_ids else
            PermissionLevel.MOD if qq_id in mod_ids else
            PermissionLevel.USER
        )
