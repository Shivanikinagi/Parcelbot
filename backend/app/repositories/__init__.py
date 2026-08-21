"""Repository layer — the single gateway to persisted data.

**All access control lives here.** Every repository is constructed with a
:class:`~app.core.security.Principal` and silently applies that principal's
account scope to every query. Higher layers (services, tools, the agent) cannot
bypass it: there is no code path to the ORM that does not pass through a
scoped repository.
"""
