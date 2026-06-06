# Production Readiness Notes

## Required Toolchain

- Python 3.12.x should be used for the packaged sidecar, even though the source supports newer Python versions.
- Node.js LTS and npm are required to install and build the React frontend.
- Rust with the MSVC target is required for Tauri.
- Ollama is not bundled into the installer; the app detects it and shows setup status.

## Packaging Flow

1. Build the Python backend sidecar with PyInstaller.
2. Copy the generated sidecar to `src-tauri/binaries/local-chatbot-backend-x86_64-pc-windows-msvc.exe`.
3. Build the React frontend into `src-tauri/dist`.
4. Run Tauri build to produce the NSIS installer.

## Production Gaps To Close Before Public Release

- Add a signed application icon set.
- Code-sign the Windows installer and app executable.
- Configure an update channel if automatic updates are desired.
- Run web search QA on clean Windows networks because web results depend on DuckDuckGo Lite availability.
- Add full OCR dependencies and installer checks for Tesseract/Poppler if OCR is marketed as scan-ready.
- Run installer QA on a clean Windows VM.

## Security Notes

- API keys are stored through the OS credential store via `keyring`.
- The backend binds to `127.0.0.1` only.
- Authenticated API routes require a per-session token produced by the sidecar process.
- Cloud providers receive retrieved snippets only when the user selects that provider.
- Web search is explicit per chat and uses public web result snippets.
