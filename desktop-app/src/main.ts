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
import * as fs from 'fs';
import { captureScreenshot } from './services/screenshot';
import { extractFromImage } from './services/ocr';
import { AuthStore } from './services/auth';
import { ApiClient } from './services/api-client';
import { config } from './config';
import ElectronStore from 'electron-store';

// ─── Window Geometry Persistence ────────────────────────────
interface WindowBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

const CHAT_MIN_WIDTH = 360;
const CHAT_MAX_WIDTH = 960;
const CHAT_MIN_HEIGHT = 72;
const CHAT_MAX_HEIGHT = 1200;
const CHAT_DEFAULT_WIDTH = 480;
const CHAT_DEFAULT_HEIGHT = 72;
const CHAT_SCREEN_MARGIN = 32;

const boundsStore = new ElectronStore<{ chatBounds?: WindowBounds }>({
  name: 'window-bounds',
  defaults: {},
});

function getValidatedChatBounds(): WindowBounds {
  const saved = boundsStore.get('chatBounds');
  const primaryDisplay = screen.getPrimaryDisplay();
  const workArea = primaryDisplay.workAreaSize;
  const workAreaPos = primaryDisplay.workArea;

  if (
    saved &&
    typeof saved.x === 'number' &&
    typeof saved.y === 'number' &&
    typeof saved.width === 'number' &&
    typeof saved.height === 'number'
  ) {
    // Clamp dimensions to valid range
    const w = Math.max(CHAT_MIN_WIDTH, Math.min(saved.width, CHAT_MAX_WIDTH, workArea.width));
    const h = Math.max(CHAT_MIN_HEIGHT, Math.min(saved.height, CHAT_MAX_HEIGHT, workArea.height));

    // Ensure the window is at least partially visible on screen
    let x = saved.x;
    let y = saved.y;
    const minVisible = 100;

    if (x + w < workAreaPos.x + minVisible) x = workAreaPos.x;
    if (x > workAreaPos.x + workArea.width - minVisible) x = workAreaPos.x + workArea.width - w;
    if (y < workAreaPos.y) y = workAreaPos.y;
    if (y > workAreaPos.y + workArea.height - minVisible) y = workAreaPos.y + workArea.height - h;

    return { x: Math.round(x), y: Math.round(y), width: Math.round(w), height: Math.round(h) };
  }

  // Default: centered horizontally, anchored near bottom
  return {
    x: Math.round((workArea.width - CHAT_DEFAULT_WIDTH) / 2) + workAreaPos.x,
    y: workAreaPos.y + workArea.height - CHAT_DEFAULT_HEIGHT - CHAT_SCREEN_MARGIN,
    width: CHAT_DEFAULT_WIDTH,
    height: CHAT_DEFAULT_HEIGHT,
  };
}

function saveChatBounds(): void {
  if (!chatWindow || chatWindow.isDestroyed()) return;
  const bounds = chatWindow.getBounds();
  boundsStore.set('chatBounds', bounds);
}

// When launched from desktop (no terminal), stdout/stderr are broken pipes.
// Silence EPIPE to prevent crash on any console.log/console.error call.
process.stdout?.on?.('error', () => {});
process.stderr?.on?.('error', () => {});

// ─── Structured Logger (issue 5a/5b) ───────────────────────
const logDir = path.join(app.getPath('userData'), 'logs');
try { fs.mkdirSync(logDir, { recursive: true }); } catch { /* ignore */ }
const logFile = path.join(logDir, `planly-${new Date().toISOString().slice(0, 10)}.log`);

function appLog(level: 'INFO' | 'WARN' | 'ERROR', context: string, msg: string, meta?: Record<string, unknown>): void {
  const line = `[${new Date().toISOString()}] [${level}] [${context}] ${msg}${meta ? ' ' + JSON.stringify(meta) : ''}\n`;
  try { fs.appendFileSync(logFile, line); } catch { /* ignore */ }
  if (level === 'ERROR') console.error(line.trim());
  else console.log(line.trim());
}

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
  const bounds = getValidatedChatBounds();

  chatWindow = new BrowserWindow({
    ...bounds,
    show: false,
    frame: false,
    alwaysOnTop: true,
    resizable: true,
    minimizable: false,
    maximizable: false,
    minWidth: CHAT_MIN_WIDTH,
    minHeight: CHAT_MIN_HEIGHT,
    maxWidth: CHAT_MAX_WIDTH,
    maxHeight: CHAT_MAX_HEIGHT,
    skipTaskbar: true,
    backgroundColor: '#1a1a2e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Persist bounds on move/resize end
  chatWindow.on('moved', () => saveChatBounds());
  chatWindow.on('resized', () => saveChatBounds());

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
    let settled = false; // Prevent double resolution (issue 2c)

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

    function tryResolve(code: string): void {
      if (settled) return;
      settled = true;
      oauthWin.close();
      resolve(code);
    }

    function tryReject(err: Error): void {
      if (settled) return;
      settled = true;
      reject(err);
    }

    oauthWin.webContents.on('will-redirect', (event, url) => {
      const parsed = new URL(url);
      const code = parsed.searchParams.get('code');
      if (code) {
        event.preventDefault();
        tryResolve(code);
        return;
      }
      const error = parsed.searchParams.get('error');
      if (error) {
        event.preventDefault();
        tryReject(new Error(error));
      }
    });

    oauthWin.webContents.on('will-navigate', (event, url) => {
      if (url.startsWith(redirectUri)) {
        const parsed = new URL(url);
        const code = parsed.searchParams.get('code');
        if (code) {
          event.preventDefault();
          tryResolve(code);
        }
      }
    });

    oauthWin.on('closed', () => {
      tryReject(new Error('OAuth window closed'));
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
    // Reset chat state to clear stale screenshot/conversation (issues 3a, 3b)
    try {
      chatWindow!.webContents.send('chat:reset');
    } catch { /* window not ready */ }
    // Restore last persisted bounds (validated against current screen)
    const restoredBounds = getValidatedChatBounds();
    chatWindow!.setBounds(restoredBounds);
    chatWindow!.show();
    chatWindow!.focus();
  }
}

function expandChatWindow(newHeight: number): void {
  if (!chatWindow || chatWindow.isDestroyed()) return;

  const primaryDisplay = screen.getPrimaryDisplay();
  const workArea = primaryDisplay.workArea;
  const currentBounds = chatWindow.getBounds();

  const clampedHeight = Math.max(
    CHAT_MIN_HEIGHT,
    Math.min(newHeight, CHAT_MAX_HEIGHT, workArea.height)
  );

  // Grow upward: keep bottom edge fixed
  const bottomY = currentBounds.y + currentBounds.height;
  let newY = bottomY - clampedHeight;

  // Don't go above the work area
  if (newY < workArea.y) newY = workArea.y;

  chatWindow.setBounds({
    x: currentBounds.x,
    y: Math.round(newY),
    width: currentBounds.width,
    height: Math.round(clampedHeight),
  });
  saveChatBounds();
}

// ─── Auth transition helper ─────────────────────────────────

async function onAuthSuccess(): Promise<void> {
  isAuthenticated = true;
  updateTrayMenu();
  appLog('INFO', 'auth', 'Authentication successful');

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

ipcMain.on('chat:move-window', (_event, deltaX: number, deltaY: number) => {
  if (!chatWindow || chatWindow.isDestroyed()) return;
  const bounds = chatWindow.getBounds();
  const primaryDisplay = screen.getPrimaryDisplay();
  const workArea = primaryDisplay.workArea;

  let newX = bounds.x + deltaX;
  let newY = bounds.y + deltaY;

  // Clamp to screen bounds
  newX = Math.max(workArea.x, Math.min(newX, workArea.x + workArea.width - bounds.width));
  newY = Math.max(workArea.y, Math.min(newY, workArea.y + workArea.height - bounds.height));

  chatWindow.setPosition(Math.round(newX), Math.round(newY));
});

ipcMain.on('chat:set-bounds', (_event, bounds: { x: number; y: number; width: number; height: number }) => {
  if (!chatWindow || chatWindow.isDestroyed()) return;
  const primaryDisplay = screen.getPrimaryDisplay();
  const workArea = primaryDisplay.workArea;

  const w = Math.max(CHAT_MIN_WIDTH, Math.min(bounds.width, CHAT_MAX_WIDTH, workArea.width));
  const h = Math.max(CHAT_MIN_HEIGHT, Math.min(bounds.height, CHAT_MAX_HEIGHT, workArea.height));
  let x = Math.max(workArea.x, Math.min(bounds.x, workArea.x + workArea.width - w));
  let y = Math.max(workArea.y, Math.min(bounds.y, workArea.y + workArea.height - h));

  chatWindow.setBounds({ x: Math.round(x), y: Math.round(y), width: Math.round(w), height: Math.round(h) });
});

ipcMain.on('chat:save-bounds', () => {
  saveChatBounds();
});

ipcMain.handle('chat:get-bounds', () => {
  if (!chatWindow || chatWindow.isDestroyed()) return null;
  return chatWindow.getBounds();
});

ipcMain.handle('chat:get-screen-info', () => {
  const primaryDisplay = screen.getPrimaryDisplay();
  return {
    workArea: primaryDisplay.workArea,
    scaleFactor: primaryDisplay.scaleFactor,
  };
});

ipcMain.handle('chat:get-constraints', () => ({
  minWidth: CHAT_MIN_WIDTH,
  maxWidth: CHAT_MAX_WIDTH,
  minHeight: CHAT_MIN_HEIGHT,
  maxHeight: CHAT_MAX_HEIGHT,
}));

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
    await onAuthSuccess(); // issue 2b: await to prevent race with UI
    return result;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Login failed';
    appLog('ERROR', 'auth:login', msg);
    throw new Error(msg);
  }
});

ipcMain.handle('auth:register', async (_event, email: string, password: string, fullName: string) => {
  try {
    const result = await apiClient.register(email, password, fullName);
    await onAuthSuccess(); // issue 2b: await to prevent race with UI
    return result;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Registration failed';
    appLog('ERROR', 'auth:register', msg);
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
    await onAuthSuccess(); // issue 2b: await to prevent race with UI
    return data;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Google OAuth failed';
    appLog('ERROR', 'auth:google-oauth', msg);
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
  try {
    await apiClient.deleteUser();
  } catch (err: unknown) {
    // Force local logout regardless of server outcome (issue 4c)
    const msg = err instanceof Error ? err.message : 'Delete account failed';
    appLog('ERROR', 'settings:delete-account', msg);
    authStore.clear();
  }

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

// ─── Agent IPC Handlers (issue 1b: route through ApiClient with auto-refresh) ──

ipcMain.handle('agent:process', async (_event, params: {
  conversation_id?: string;
  user_prompt: string;
  messages: { username: string; text: string; timestamp: string }[];
  screenshot_metadata: { ocr_confidence: number; raw_text?: string };
}) => {
  const requestId = `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  appLog('INFO', 'agent:process', `Sending request ${requestId}`, {
    conversation_id: params.conversation_id,
    prompt_length: params.user_prompt.length,
    message_count: params.messages.length,
  });

  try {
    const response = await apiClient.processConversation(params);
    appLog('INFO', 'agent:process', `Response ${requestId}`, {
      conversation_id: response.conversation_id,
      block_count: response.blocks?.length ?? 0,
    });
    return response;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Agent process failed';
    appLog('ERROR', 'agent:process', `Failed ${requestId}: ${msg}`);
    throw new Error(msg);
  }
});

ipcMain.handle('agent:confirm', async (_event, conversationId: string, actionIds: string[]) => {
  const requestId = `confirm_${Date.now()}`;
  appLog('INFO', 'agent:confirm', `Confirming ${requestId}`, { conversationId, actionIds });

  try {
    const response = await apiClient.confirmActions(conversationId, actionIds);
    appLog('INFO', 'agent:confirm', `Response ${requestId}`, {
      result_count: response.results?.length ?? 0,
    });
    return response;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Confirm actions failed';
    appLog('ERROR', 'agent:confirm', `Failed ${requestId}: ${msg}`);
    throw new Error(msg);
  }
});

// ─── OCR IPC Handler (issue 6a: run in main process, off the renderer thread) ──

ipcMain.handle('ocr:run', async (_event, imageBase64: string) => {
  appLog('INFO', 'ocr', `Starting OCR, image size: ${Math.round(imageBase64.length / 1024)}KB`);
  try {
    const result = await extractFromImage(imageBase64);
    appLog('INFO', 'ocr', `OCR complete`, {
      confidence: result.confidence,
      message_count: result.messages.length,
      text_length: result.rawText.length,
    });
    return result;
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'OCR failed';
    appLog('ERROR', 'ocr', msg);
    throw new Error(msg);
  }
});

// ─── Renderer Error Forwarding (issue 5a) ───────────────────

ipcMain.on('renderer:error', (_event, context: string, error: string) => {
  appLog('ERROR', `renderer:${context}`, error);
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

  // Step 1: Health check (async — no longer blocks main thread, issue 4a)
  sendSplashStatus('Connecting...');
  let healthy = false;
  try {
    healthy = await apiClient.healthCheck();
  } catch {
    // Health check failed
  }
  appLog('INFO', 'startup', `Health check result: ${healthy}`);

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
