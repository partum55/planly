# Planly Desktop — Build & Release Guide

## Prerequisites

- Node.js 20+
- npm (ships with Node)
- Platform-specific:
  - **Linux**: `libfuse2` (for AppImage), `dpkg` (for .deb — usually pre-installed)
  - **macOS**: Xcode command-line tools (`xcode-select --install`)
  - **Windows**: no extra deps; NSIS is downloaded automatically by electron-builder

## Scripts

| Script | What it does |
|---|---|
| `npm run lint` | Type-check without emitting |
| `npm run compile` | Build vendor + compile TypeScript |
| `npm run pack` | Compile + produce unpacked app (for quick testing) |
| `npm run dist` | Compile + build installers for current platform |
| `npm run dist:linux` | Build Linux installers (AppImage + .deb) |
| `npm run dist:win` | Build Windows installer (.exe) |
| `npm run dist:mac` | Build macOS installer (.dmg) |

### Build locally

```bash
cd desktop-app
npm install
npm run dist
# Output in desktop-app/release/
```

## How to cut a release

1. Update `version` in `desktop-app/package.json` (semver, e.g. `1.2.0`).
2. Commit: `git commit -am "release: v1.2.0"`
3. Tag: `git tag v1.2.0`
4. Push: `git push origin main --tags`
5. CI builds all platforms, creates a **draft** GitHub Release with installers attached.
6. Go to GitHub Releases, review the draft, edit notes if needed, publish.

> **Important**: the tag version must match `package.json` version exactly (e.g. tag `v1.2.0` ↔ version `"1.2.0"`). CI will fail if they don't match.

## CI/CD overview

Workflow: `.github/workflows/desktop-release.yml`

| Trigger | What happens |
|---|---|
| PR touching `desktop-app/` | Smoke build on all 3 platforms (no artifacts uploaded) |
| Push to `main` | Build + upload artifacts (14-day retention) |
| Tag `v*.*.*` | Build + create draft GitHub Release with installers |

Matrix: `ubuntu-latest`, `windows-latest`, `macos-latest`.

## Code signing (optional)

Builds work without signing. To enable:

### Windows

Add these GitHub Secrets:

| Secret | Description |
|---|---|
| `WIN_CSC_LINK` | Base64-encoded `.pfx` certificate |
| `WIN_CSC_KEY_PASSWORD` | Certificate password |

### macOS

| Secret | Description |
|---|---|
| `MAC_CSC_LINK` | Base64-encoded `.p12` Developer ID certificate |
| `MAC_CSC_KEY_PASSWORD` | Certificate password |
| `APPLE_ID` | Apple ID email for notarization |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password (appleid.apple.com) |
| `APPLE_TEAM_ID` | 10-char team identifier |

## Troubleshooting

### Linux: AppImage fails with "fuse: not found"

```bash
sudo apt-get install libfuse2
```

### Linux: `cannot execute binary file` on AppImage

```bash
chmod +x Planly-*.AppImage
```

### macOS: "App is damaged and can't be opened"

Unsigned builds trigger Gatekeeper. Remove quarantine attribute:

```bash
xattr -cr /Applications/Planly.app
```

### Windows: SmartScreen warning

Expected for unsigned builds. Users can click "More info" → "Run anyway".

### node-gyp / native modules fail

Ensure Python 3 and C++ build tools are available:

- **Linux**: `sudo apt-get install build-essential python3`
- **macOS**: `xcode-select --install`
- **Windows**: `npm install -g windows-build-tools` (admin PowerShell)

### electron-builder cache issues

Clear the cache:

```bash
# Linux
rm -rf ~/.cache/electron-builder ~/.cache/electron

# macOS
rm -rf ~/Library/Caches/electron-builder ~/Library/Caches/electron

# Windows
rmdir /s /q %LOCALAPPDATA%\electron-builder\Cache
```
