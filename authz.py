"""Server-side roles. The browser never decides who is an admin or a broker."""
from __future__ import annotations

ALLOWED_ROLES = {'buyer', 'seller', 'broker', 'mechanic', 'charter_operator', 'other'}


def user_roles(user: dict | None) -> set[str]:
    if not user:
        return set()
    roles = set()
    primary = (user.get('profile_role') or '').strip().lower()
    if primary in ALLOWED_ROLES:
        roles.add(primary)
    extra = user.get('roles') or ''
    if isinstance(extra, str):
        for part in extra.split(','):
            role = part.strip().lower()
            if role in ALLOWED_ROLES:
                roles.add(role)
    return roles


def has_role(user: dict | None, role: str) -> bool:
    if not user:
        return False
    if role == 'admin':
        return bool(user.get('is_admin'))
    return role in user_roles(user)


def is_broker(user: dict | None) -> bool:
    return bool(user) and (bool(user.get('is_admin')) or has_role(user, 'broker'))


def is_operator(user: dict | None) -> bool:
    return bool(user) and (bool(user.get('is_admin')) or has_role(user, 'charter_operator'))


def clean_roles(value) -> str:
    """Comma-separated extra roles. Admin is never accepted from a form."""
    if not value:
        return ''
    kept = []
    for part in str(value).split(','):
        role = part.strip().lower()
        if role in ALLOWED_ROLES and role not in kept:
            kept.append(role)
    return ','.join(kept)
