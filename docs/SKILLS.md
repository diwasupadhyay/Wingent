# Trusted Wingent capabilities

The operator discovers tool names and schemas from the runtime registry; it does not have an application action enum. A capability extension supplies `register(registry)` and calls `registry.register(...)` with a strict Pydantic input model, output model, permission, timeout, retry semantics and optional precondition/observer/verifier. Add concise `Capability` guidance if useful. Guidance never grants permission.

For an installed Python distribution, expose that callable under the `wingent.skills` entry-point group. Explicitly enable its entry-point name with `WINGENT_SKILLS=name1,name2` before backend startup. Missing/ambiguous registrations fail startup visibly; replacing existing tools is rejected. No entries are loaded by default. Names `ask`, `finish`, and `answer` are reserved for operator decisions.

This loader executes trusted Python code with backend privileges. It is **not a sandbox** and is never callable by the model. Review/install extensions deliberately. Package them and their entry-point metadata with the sidecar before enabling them in a frozen release; arbitrary host-package loading into the EXE is not supported or tested.

Tests use a synthetic installed-entry-point provider. No third-party plugin has been installed or loaded on the user's machine. `file_tools.py` is a bundled provider demonstrating general discovery, observation and artifact creation using the same registry.
