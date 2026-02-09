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

// When launched from desktop (no terminal), stdout/stderr are broken pipes.
// Silence EPIPE to prevent crash on any console.log/console.error call.
process.stdout?.on?.('error', () => {});
process.stderr?.on?.('error', () => {});

// no-sandbox is passed via CLI or .desktop launcher — no appendSwitch needed

const authStore = new AuthStore();
const apiClient = new ApiClient(config.API_BASE_URL, authStore);

let mainWindow: BrowserWindow | null = null;
let chatWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let isAuthenticated = false;
let isQuitting = false;

// ─── Single Instance Lock ───────────────────────────────────
const gotLock = app.requestSingleInstanceLock();

if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// ─── Navigation Helpers ─────────────────────────────────────

function navigateTo(view: string): void {
  try {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('navigate', view);
    }
  } catch {
    // Window or webContents destroyed — ignore
  }
}

function sendSplashStatus(status: string): void {
  try {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('splash:status', status);
    }
  } catch {
    // Window or webContents destroyed — ignore
  }
}

function sendUserInfo(info: { name: string }): void {
  try {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('user:info', info);
    }
  } catch {
    // Window or webContents destroyed — ignore
  }
}

// ─── Window Factories ───────────────────────────────────────

function createMainWindow(): void {
  mainWindow = new BrowserWindow({
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

  mainWindow.loadFile(path.join(__dirname, '..', 'src', 'ui', 'app.html'));

  mainWindow.webContents.on('before-input-event', (_event, input) => {
    if (input.key === 'Escape' && input.type === 'keyDown') {
      mainWindow?.hide();
    }
  });

  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow?.hide();
    }
  });
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

  chatWindow.webContents.on('console-message', (_e, _level, msg) => {
    console.log('[chat]', msg);
  });

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
          apiClient.logout();
          isAuthenticated = false;
          updateTrayMenu();
          if (chatWindow && !chatWindow.isDestroyed()) {
            chatWindow.hide();
          }
          navigateTo('login');
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.show();
            mainWindow.focus();
          }
        } else {
          navigateTo('login');
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.show();
            mainWindow.focus();
          }
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
      navigateTo('login');
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.show();
        mainWindow.focus();
      }
      return;
    }
    // Hide main window when showing chat
    if (mainWindow && !mainWindow.isDestroyed() && mainWindow.isVisible()) {
      mainWindow.hide();
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

async function onAuthSuccess(): Promise<void> {
  isAuthenticated = true;
  updateTrayMenu();

  // Show mainWindow with splash
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show();
  }
  navigateTo('splash');

  const me = await apiClient.getMe();
  const name = me?.full_name || me?.email || '';
  sendSplashStatus(name ? `Welcome, ${name}!` : 'Welcome!');

  await new Promise((r) => setTimeout(r, 1500));

  sendUserInfo({ name: name || 'User' });
  navigateTo('home');
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
  console.log('chat:screenshot called');
  const wasVisible = chatWindow?.isVisible() ?? false;
  if (wasVisible) chatWindow!.hide();

  await new Promise((r) => setTimeout(r, 150));

  try {
    const result = await captureScreenshot();
    console.log('screenshot OK, base64 length:', result.imageBase64.length);
    return result;
  } catch (err) {
    console.error('screenshot FAILED:', err);
    throw err;
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

// ─── Settings IPC Handlers ──────────────────────────────────

ipcMain.handle('settings:delete-account', async () => {
  await apiClient.deleteUser();
  isAuthenticated = false;
  updateTrayMenu();

  if (chatWindow && !chatWindow.isDestroyed()) {
    chatWindow.hide();
  }

  navigateTo('login');
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show();
    mainWindow.focus();
  }
});

ipcMain.handle('settings:logout', async () => {
  await apiClient.logout();
  isAuthenticated = false;
  updateTrayMenu();

  // Hide chat window
  if (chatWindow && !chatWindow.isDestroyed()) {
    chatWindow.hide();
  }

  // Navigate to login in same mainWindow
  navigateTo('login');
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show();
    mainWindow.focus();
  }
});

ipcMain.on('settings:quit', () => {
  isQuitting = true;
  app.quit();
});

// ─── App Lifecycle ──────────────────────────────────────────

app.whenReady().then(() => {
  startup().catch(() => {});
});

async function startup(): Promise<void> {
  createMainWindow();

  const MIN_SPLASH_MS = 1500;
  const splashShownAt = Date.now();

  try {
    createTray();
  } catch {
    // Tray may fail on some environments — non-fatal
  }

  registerShortcut();

  const waitSplash = async () => {
    const elapsed = Date.now() - splashShownAt;
    if (elapsed < MIN_SPLASH_MS) {
      await new Promise((r) => setTimeout(r, MIN_SPLASH_MS - elapsed));
    }
  };

  // Step 1: Health check
  sendSplashStatus('Connecting...');
  let healthy = false;
  try {
    const { execSync } = require('child_process');
    const stdout = execSync(`curl -s --connect-timeout 5 ${config.API_BASE_URL}/health`, { encoding: 'utf-8', timeout: 8000 });
    const data = JSON.parse(stdout);
    healthy = data.status === 'ok';
  } catch {
    // Health check failed
  }

  if (!healthy) {
    sendSplashStatus('Service unavailable');
    await waitSplash();
    await new Promise((r) => setTimeout(r, 2000));
    isQuitting = true;
    app.quit();
    return;
  }

  // Step 2: Check auth
  if (authStore.isAuthenticated()) {
    sendSplashStatus('Signing in...');
    const refreshed = await apiClient.refreshToken();

    if (refreshed) {
      isAuthenticated = true;
      updateTrayMenu();

      const me = await apiClient.getMe();
      const name = me?.full_name || me?.email || '';
      sendSplashStatus(name ? `Welcome, ${name}!` : 'Welcome!');

      await waitSplash();
      await new Promise((r) => setTimeout(r, 1200));

      sendUserInfo({ name: name || 'User' });
      navigateTo('home');
    } else {
      sendSplashStatus('Session expired');
      await waitSplash();
      await new Promise((r) => setTimeout(r, 800));
      navigateTo('login');
    }
  } else {
    await waitSplash();
    navigateTo('login');
  }
}

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
