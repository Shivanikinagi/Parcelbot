"""Tool layer — the typed, validated capabilities the agent can invoke.

Every tool declares a Pydantic input schema, a permission requirement, and
whether it changes state. The :class:`~app.tools.base.Tool.execute` wrapper
enforces validation, RBAC, timing, telemetry, and error containment uniformly,
so no individual tool can skip a safety check. State-changing tools never
mutate on ``execute`` — they *prepare* a proposed action that the agent surfaces
for confirmation, and only ``commit`` after the user approves.
"""
