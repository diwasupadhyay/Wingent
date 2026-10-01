# Decisions

## Bounded planning before broader automation
Use Ollama JSON-schema output to translate natural requests into at most eight typed actions, retaining a deterministic fast path. Compile semantic searches into URLs in trusted code, validate all steps before launch, and report actual tool acceptance. A malformed model plan gets one bounded format repair, never a side-effect retry. This establishes a usable planning/execution boundary without introducing arbitrary shell execution or pretending that launches verify page contents. Browser observation is a separate next milestone.

## Launcher overlay
Wingent uses a fixed-width, borderless, always-on-top surface that stays out of the taskbar. It expands only for useful progress or output and uses explicit tray Quit semantics.

## Frozen backend sidecar
The Windows package includes a PyInstaller-built FastAPI binary named for the Rust target triple. Tauri launches it only when port 8000 is free and owns the spawned process, removing the end-user Python requirement.

## Local-first model default
We default to Ollama to avoid network dependencies and keep the app local-first.

## Streaming before full chat history
The first version streams partial outputs to the UI for a faster perceived response and better cancellation UX.

## Minimal but structured state
The app keeps a clear status and message lifecycle instead of relying on loose chat history.

## Complete deterministic commands
Safe actions execute without a model only when every requested step matches a supported command. This prevents a partial browser launch from being reported as a completed inbox inspection. Unhandled action requests receive an explicit error.

## Optional second model tier
`OLLAMA_MODEL` remains the fast default. `OLLAMA_COMPLEX_MODEL` is opt-in for long and analysis-style text prompts. This adds useful routing without requiring a second model installation for the normal build.

## No speculative automation yet
Browser automation, desktop control, and voice are intentionally deferred until the command bar and backend loop are proven.
