# GitHub Publishing Guide

This guide explains how to prepare and publish Local AI Chatbot as a clean GitHub repository.

## 1. Prepare The Repository

Start from the project root:

```powershell
cd C:\Users\moone\OneDrive\Desktop\Local_Chatbot
```

Review generated files before publishing:

```powershell
Get-ChildItem -Force
```

Generated folders such as `.venv`, `build`, `dist`, `cargo-target`, caches, and installer outputs should not be committed. They are ignored by `.gitignore`.

## 2. Recommended Repository Contents

Commit source code, build scripts, docs, and lockfiles:

```text
README.md
.gitignore
pyproject.toml
docs/
scripts/
backend/
frontend/
src-tauri/
frontend/package-lock.json
src-tauri/Cargo.lock
```

Do not commit generated artifacts:

```text
.venv/
build/
dist/
cargo-target/
frontend/node_modules/
frontend/dist/
src-tauri/dist/
src-tauri/target/
src-tauri/binaries/*.exe
*.spec
*.log
installers/
```

The backend sidecar executable is generated with:

```powershell
.\scripts\build_backend.ps1
```

The Windows installer is generated with:

```powershell
.\scripts\build_windows.ps1
```

## 3. Initialize Git

If the folder is not already a Git repository:

```powershell
git init
git branch -M main
```

Check what Git sees:

```powershell
git status
```

If generated files appear, update `.gitignore` before committing.

## 4. Stage Files

Stage all repository files:

```powershell
git add .
```

Review staged files:

```powershell
git status
git diff --cached --stat
```

Optional detailed review:

```powershell
git diff --cached
```

## 5. Make The First Commit

Use a clear initial commit message:

```powershell
git commit -m "Initial production-ready Local AI Chatbot app"
```

## 6. Create A GitHub Repository

On GitHub:

1. Go to `https://github.com/new`.
2. Choose a repository name, for example `local-ai-chatbot`.
3. Add a short description:

   ```text
   Windows desktop local AI chatbot for private document search with citations.
   ```

4. Do not initialize with a README, `.gitignore`, or license if those already exist locally.
5. Create the repository.

## 7. Connect Local Git To GitHub

Replace `YOUR_USERNAME` with your GitHub username:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/local-ai-chatbot.git
git push -u origin main
```

If a remote already exists:

```powershell
git remote -v
git remote set-url origin https://github.com/YOUR_USERNAME/local-ai-chatbot.git
git push -u origin main
```

## 8. Add A Release Build

Build the installer locally:

```powershell
.\scripts\build_backend.ps1
.\scripts\build_windows.ps1
```

The installer is produced at:

```text
cargo-target/release/bundle/nsis/Local AI Chatbot_0.1.0_x64-setup.exe
```

Create a GitHub release:

1. Go to the repository on GitHub.
2. Open `Releases`.
3. Click `Draft a new release`.
4. Create a tag such as `v0.1.0`.
5. Title the release `Local AI Chatbot v0.1.0`.
6. Upload the NSIS installer `.exe`.
7. Add release notes summarizing major features and known requirements.

Example release notes:

```markdown
## Local AI Chatbot v0.1.0

Initial Windows release.

### Features

- Local document chat with citations
- File and recursive folder import
- Multiple saved chats
- Chat-specific sources
- Ollama local model support
- Optional no-key DuckDuckGo Lite web search
- BYO API-key support for OpenAI, Claude, Gemini, and Grok
- Windows NSIS installer

### Requirements

- Windows 10 or Windows 11
- Ollama installed for local model generation
```

## 9. Repository Best Practices

- Keep generated artifacts out of Git.
- Commit lockfiles for reproducible frontend and Tauri builds.
- Keep secrets out of the repository.
- Never commit `.env` files or API keys.
- Add screenshots or demo GIFs only after verifying they do not show private documents.
- Use GitHub Releases for installer `.exe` files instead of committing them directly.
- Keep the README focused on users and new developers.
- Keep production notes in `docs/PRODUCTION.md`.
- Use short, meaningful commit messages.

## 10. Suggested GitHub Repository Settings

Recommended repository settings:

- Enable Issues if you want bug reports and feature requests.
- Enable Discussions only if you want community Q&A.
- Add repository topics:

```text
tauri
react
typescript
python
fastapi
ollama
local-ai
rag
desktop-app
windows
document-search
```

- Add branch protection later if multiple people work on the project.
- Add a license before making the repository public.

## 11. Suggested Future Files

These files are not required, but they are useful for a public project:

```text
LICENSE
CONTRIBUTING.md
SECURITY.md
CHANGELOG.md
.github/ISSUE_TEMPLATE/bug_report.md
.github/ISSUE_TEMPLATE/feature_request.md
```

## 12. Clean Verification Before Push

Before pushing or publishing a release, run:

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check backend
cd frontend
npm run build
cd ..
.\scripts\build_backend.ps1
.\scripts\build_windows.ps1
```

Then confirm:

```powershell
git status
```

Only source, documentation, and configuration changes should be staged.
