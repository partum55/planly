import {
  app,
  BrowserWindow,
  ipcMain,
  Tray,
  Menu,
  screen,
  nativeImage,
  globalShortcut,
} from 'electron';
import * as path from 'path';
import { captureScreenshot } from './services/screenshot';
import { AuthStore } from './services/auth';
import { ApiClient } from './services/api-client';
import { config } from './config';

// Disable sandbox for Linux (SUID sandbox not available in AppImage)
if (process.platform === 'linux') {
  app.commandLine.appendSwitch('no-sandbox');
}

const authStore = new AuthStore();
const apiClient = new ApiClient(config.API_BASE_URL, authStore);

let chatWindow: BrowserWindow | null = null;
let loginWindow: BrowserWindow | null = null;
let startWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let isAuthenticated = false;
let isQuitting = false;

// ─── Single Instance Lock ───────────────────────────────────
const gotLock = app.requestSingleInstanceLock();

if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    toggleChatWindow();
  });
}

// ─── Window Factories ───────────────────────────────────────

function createStartWindow(): void {
  startWindow = new BrowserWindow({
    width: 360,
    height: 400,
    frame: false,
    resizable: false,
    backgroundColor: '#1a1a2e',
    center: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  startWindow.loadFile(path.join(__dirname, '..', 'src', 'ui', 'start.html'));

  startWindow.on('closed', () => {
    startWindow = null;
  });
}

function sendStartStatus(status: string): void {
  if (startWindow && !startWindow.isDestroyed()) {
    startWindow.webContents.send('start:status', status);
  }
}

function createChatWindow(): void {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  const winWidth = 480;
  const winHeight = 72;

  chatWindow = new BrowserWindow({
    width: winWidth,
    height: winHeight,
    x: Math.round((screenWidth - winWidth) / 2),
    y: screenHeight - winHeight - 32,
    show: false,
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    backgroundColor: '#1a1a2e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  chatWindow.loadFile(path.join(__dirname, '..', 'src', 'ui', 'chat.html'));

  chatWindow.webContents.on('before-input-event', (_event, input) => {
    if (input.key === 'Escape' && input.type === 'keyDown') {
      chatWindow?.hide();
    }
  });

  chatWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      chatWindow?.hide();
    }
  });
}

function createLoginWindow(): void {
  loginWindow = new BrowserWindow({
    width: 400,
    height: 580,
    frame: false,
    resizable: false,
    backgroundColor: '#1a1a2e',
    center: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  loginWindow.loadFile(path.join(__dirname, '..', 'src', 'ui', 'login.html'));

  loginWindow.webContents.on('before-input-event', (_event, input) => {
    if (input.key === 'Escape' && input.type === 'keyDown') {
      loginWindow?.close();
    }
  });

  loginWindow.on('closed', () => {
    loginWindow = null;
  });
}

function createOAuthWindow(): Promise<string> {
  return new Promise((resolve, reject) => {
    const redirectUri = `${config.API_BASE_URL}/auth/google/callback`;
    const authUrl =
      'https://accounts.google.com/o/oauth2/v2/auth' +
      `?client_id=${encodeURIComponent(config.GOOGLE_CLIENT_ID)}` +
      `&redirect_uri=${encodeURIComponent(redirectUri)}` +
      '&response_type=code' +
      '&scope=openid%20email%20profile' +
      '&access_type=offline' +
      '&prompt=consent';

    const oauthWin = new BrowserWindow({
      width: 500,
      height: 700,
      backgroundColor: '#fff',
      webPreferences: {
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    oauthWin.loadURL(authUrl);

    // Intercept the redirect to capture the authorization code
    oauthWin.webContents.on('will-redirect', (_event, url) => {
      const parsed = new URL(url);
      const code = parsed.searchParams.get('code');
      if (code) {
        oauthWin.close();
        resolve(code);
      }
      const error = parsed.searchParams.get('error');
      if (error) {
        oauthWin.close();
        reject(new Error(error));
      }
    });

    // Also check navigation (some flows use navigation instead of redirect)
    oauthWin.webContents.on('will-navigate', (_event, url) => {
      if (url.startsWith(redirectUri)) {
        const parsed = new URL(url);
        const code = parsed.searchParams.get('code');
        if (code) {
          oauthWin.close();
          resolve(code);
        }
      }
    });

    oauthWin.on('closed', () => {
      reject(new Error('OAuth window closed'));
    });
  });
}

function updateTrayMenu(): void {
  if (!tray) return;

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open Planly',
      click: () => toggleChatWindow(),
    },
    { type: 'separator' },
    {
      label: isAuthenticated ? 'Logout' : 'Login',
      click: () => {
        if (isAuthenticated) {
          authStore.clear();
          isAuthenticated = false;
          updateTrayMenu();
        } else {
          if (!loginWindow || loginWindow.isDestroyed()) {
            createLoginWindow();
          }
          loginWindow?.show();
          loginWindow?.focus();
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);
}

// ─── Chat Toggle ────────────────────────────────────────────

function toggleChatWindow(): void {
  if (!chatWindow || chatWindow.isDestroyed()) {
    createChatWindow();
  }

  if (chatWindow!.isVisible()) {
    chatWindow!.hide();
  } else {
    if (!isAuthenticated) {
      if (!loginWindow || loginWindow.isDestroyed()) {
        createLoginWindow();
      }
      loginWindow?.show();
      loginWindow?.focus();
      return;
    }
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;
    const winWidth = 480;
    const winHeight = 72;
    chatWindow!.setBounds({
      x: Math.round((screenWidth - winWidth) / 2),
      y: screenHeight - winHeight - 32,
      width: winWidth,
      height: winHeight,
    });
    chatWindow!.show();
    chatWindow!.focus();
  }
}

function expandChatWindow(newHeight: number): void {
  if (!chatWindow || chatWindow.isDestroyed()) return;

  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;
  const winWidth = 480;
  const clampedHeight = Math.min(newHeight, screenHeight - 64);

  chatWindow.setBounds({
    x: Math.round((screenWidth - winWidth) / 2),
    y: screenHeight - clampedHeight - 32,
    width: winWidth,
    height: clampedHeight,
  });
}

// ─── Auth transition helper ─────────────────────────────────

function onAuthSuccess(): void {
  isAuthenticated = true;
  updateTrayMenu();

  // Close start window if open
  if (startWindow && !startWindow.isDestroyed()) {
    startWindow.close();
    startWindow = null;
  }

  // Close login window if open
  if (loginWindow && !loginWindow.isDestroyed()) {
    loginWindow.close();
    loginWindow = null;
  }

  // Show chat
  toggleChatWindow();
}

// ─── IPC Handlers ───────────────────────────────────────────

ipcMain.on('chat:close', () => {
  chatWindow?.hide();
});

ipcMain.on('chat:resize', (_event, height: number) => {
  expandChatWindow(height);
});

ipcMain.handle('config:get', () => ({
  apiBaseUrl: config.API_BASE_URL,
}));

ipcMain.handle('chat:screenshot', async () => {
  const wasVisible = chatWindow?.isVisible() ?? false;
  if (wasVisible) chatWindow!.hide();

  await new Promise((r) => setTimeout(r, 150));

  try {
    const result = await captureScreenshot();
    return result;
  } finally {
    if (wasVisible) {
      chatWindow!.show();
      chatWindow!.focus();
    }
  }
});

// ─── Auth IPC Handlers ──────────────────────────────────────

ipcMain.handle('auth:get-token', () => {
  return authStore.getAccessToken();
});

ipcMain.handle('auth:login', async (_event, email: string, password: string) => {
  try {
    const result = await apiClient.login(email, password);
    onAuthSuccess();
    return result;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Login failed';
    throw new Error(msg);
  }
});

ipcMain.handle('auth:register', async (_event, email: string, password: string, fullName: string) => {
  try {
    const result = await apiClient.register(email, password, fullName);
    onAuthSuccess();
    return result;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Registration failed';
    throw new Error(msg);
  }
});

ipcMain.handle('auth:google-oauth', async () => {
  try {
    const code = await createOAuthWindow();

    // Send code to backend to exchange for tokens
    const { default: axios } = await import('axios');
    const { data } = await axios.post<{ access_token: string; refresh_token: string; user_id: string }>(
      `${config.API_BASE_URL}/auth/google/callback`,
      { code }
    );

    authStore.setTokens(data.access_token, data.refresh_token);
    onAuthSuccess();
    return data;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Google OAuth failed';
    throw new Error(msg);
  }
});

ipcMain.handle('auth:logout', () => {
  authStore.clear();
  isAuthenticated = false;
  updateTrayMenu();
});

ipcMain.handle('auth:check', () => {
  return authStore.isAuthenticated();
});

// ─── Legacy IPC (kept for compatibility) ────────────────────

ipcMain.on('login:success', (_event, tokens: { access_token: string; refresh_token: string }) => {
  authStore.setTokens(tokens.access_token, tokens.refresh_token);
  onAuthSuccess();
});

ipcMain.on('login:close', () => {
  if (loginWindow && !loginWindow.isDestroyed()) {
    loginWindow.close();
    loginWindow = null;
  }
});

// ─── App Lifecycle ──────────────────────────────────────────

app.whenReady().then(async () => {
  // Always show start window first
  createStartWindow();

  try {
    createTray();
  } catch (err) {
    console.error('Tray not available');
  }

  registerShortcut();

  // Check for saved tokens
  if (authStore.isAuthenticated()) {
    sendStartStatus('Connecting...');

    const refreshed = await apiClient.refreshToken();
    if (refreshed) {
      sendStartStatus('Connected!');

      // Brief pause so user sees "Connected!"
      await new Promise((r) => setTimeout(r, 600));
      onAuthSuccess();
    } else {
      sendStartStatus('Session expired');
      await new Promise((r) => setTimeout(r, 800));

      if (startWindow && !startWindow.isDestroyed()) {
        startWindow.close();
        startWindow = null;
      }
      createLoginWindow();
    }
  } else {
    sendStartStatus('Welcome!');

    // Brief splash then login
    await new Promise((r) => setTimeout(r, 1200));

    if (startWindow && !startWindow.isDestroyed()) {
      startWindow.close();
      startWindow = null;
    }
    createLoginWindow();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('window-all-closed', () => {
  // Never quit here — app lives in tray / background
});

// ─── Tray ───────────────────────────────────────────────────

function createTray(): void {
  const icon = nativeImage.createFromDataURL(
    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAMklEQVQ4T2NkYPj/n4EBCRiRBZgYyABDwwWMDIyM/xkYGP4zMDL8Z2Bg+M/AwPAfAACvYQkRx4+LOAAAAABJRU5ErkJggg=='
  );

  tray = new Tray(icon);
  tray.setToolTip('Planly');
  updateTrayMenu();
}

// ─── Shortcut Registration ───────────────────────────────────

function registerShortcut(): void {
  if (process.platform === 'linux') {
    registerGnomeShortcut();
  } else {
    registerElectronShortcut();
  }
}

function registerElectronShortcut(): void {
  globalShortcut.register('CommandOrControl+Alt+J', () => {
    toggleChatWindow();
  });

  app.on('will-quit', () => {
    globalShortcut.unregisterAll();
  });
}

// ─── GNOME Shortcut Registration ────────────────────────────

function registerGnomeShortcut(): void {
  const { execSync } = require('child_process');
  const fs = require('fs');
  const os = require('os');

  const dataDir = path.join(os.homedir(), '.local', 'share', 'planly');
  fs.mkdirSync(dataDir, { recursive: true });

  const pidFile = path.join(dataDir, 'planly.pid');
  fs.writeFileSync(pidFile, String(process.pid));

  process.on('SIGUSR1', () => {
    toggleChatWindow();
  });

  const toggleScript = path.join(dataDir, 'planly-toggle.sh');
  const scriptContent = `#!/bin/bash
PID=$(cat ${pidFile} 2>/dev/null)
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  kill -USR1 "$PID"
fi
`;
  fs.writeFileSync(toggleScript, scriptContent, { mode: 0o755 });

  try {
    const existing = execSync(
      "gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings",
      { encoding: 'utf-8' }
    ).trim();

    const kbPath = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/planly/';

    if (!existing.includes('planly')) {
      let paths: string[];
      if (existing === '@as []' || existing === '[]') {
        paths = [kbPath];
      } else {
        const cleaned = existing.replace(/@as /, '').replace(/[\[\]']/g, '');
        paths = cleaned.split(',').map((s: string) => s.trim()).filter(Boolean);
        paths.push(kbPath);
      }

      const pathsStr = '[' + paths.map((p: string) => `'${p}'`).join(', ') + ']';
      execSync(
        `gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "${pathsStr}"`
      );
    }

    const base = 'org.gnome.settings-daemon.plugins.media-keys.custom-keybinding';
    const schemaPath = kbPath;
    execSync(`gsettings set ${base}:${schemaPath} name 'Planly Toggle'`);
    execSync(`gsettings set ${base}:${schemaPath} command '${toggleScript}'`);
    execSync(`gsettings set ${base}:${schemaPath} binding '<Ctrl><Alt>j'`);

  } catch (err) {
    console.error('Could not register GNOME shortcut:', (err as Error).message);
  }
}
