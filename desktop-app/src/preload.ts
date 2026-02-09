const { contextBridge, ipcRenderer } = require('electron');

// ─── Listener cleanup registry ──────────────────────────────
// Prevents listener leaks on page reload (issue 7c).
const registeredListeners: Array<{ channel: string; handler: (...args: any[]) => void }> = [];

function safeOn(channel: string, handler: (...args: any[]) => void) {
  ipcRenderer.on(channel, handler);
  registeredListeners.push({ channel, handler });
}

// Clean up all listeners when the page unloads (dev-tools reload, navigation)
(globalThis as any).addEventListener?.('beforeunload', () => {
  for (const { channel, handler } of registeredListeners) {
    ipcRenderer.removeListener(channel, handler);
  }
  registeredListeners.length = 0;
});

contextBridge.exposeInMainWorld('planly', {
  // Config
  getConfig: () => ipcRenderer.invoke('config:get'),

  // Chat window controls
  closeChat: () => ipcRenderer.send('chat:close'),
  resizeChat: (height: number) => ipcRenderer.send('chat:resize', height),
  resetChat: (callback: () => void) => {
    const handler = () => callback();
    safeOn('chat:reset', handler);
  },

  // Window geometry (drag & resize support)
  moveWindow: (deltaX: number, deltaY: number) => ipcRenderer.send('chat:move-window', deltaX, deltaY),
  setWindowBounds: (bounds: { x: number; y: number; width: number; height: number }) =>
    ipcRenderer.send('chat:set-bounds', bounds),
  saveWindowBounds: () => ipcRenderer.send('chat:save-bounds'),
  getWindowBounds: () => ipcRenderer.invoke('chat:get-bounds') as Promise<{ x: number; y: number; width: number; height: number } | null>,
  getScreenInfo: () => ipcRenderer.invoke('chat:get-screen-info') as Promise<{ workArea: { x: number; y: number; width: number; height: number }; scaleFactor: number }>,
  getWindowConstraints: () => ipcRenderer.invoke('chat:get-constraints') as Promise<{ minWidth: number; maxWidth: number; minHeight: number; maxHeight: number }>,

  // Screenshot
  takeScreenshot: () => ipcRenderer.invoke('chat:screenshot'),

  // Auth (IPC-based — main process owns tokens)
  getToken: () => ipcRenderer.invoke('auth:get-token'),
  login: (email: string, password: string) =>
    ipcRenderer.invoke('auth:login', email, password),
  register: (email: string, password: string, fullName: string) =>
    ipcRenderer.invoke('auth:register', email, password, fullName),
  startGoogleOAuth: () => ipcRenderer.invoke('auth:google-oauth'),
  logout: () => ipcRenderer.invoke('auth:logout'),
  checkAuth: () => ipcRenderer.invoke('auth:check'),

  // Settings / app controls
  logoutAndRestart: () => ipcRenderer.invoke('settings:logout'),
  deleteAccount: () => ipcRenderer.invoke('settings:delete-account'),
  quitApp: () => ipcRenderer.send('settings:quit'),

  // Agent calls — routed through main process ApiClient (issue 1b)
  agentProcess: (params: {
    conversation_id?: string;
    user_prompt: string;
    messages: { username: string; text: string; timestamp: string }[];
    screenshot_metadata: { ocr_confidence: number; raw_text?: string };
  }) => ipcRenderer.invoke('agent:process', params),

  agentConfirm: (conversationId: string, actionIds: string[]) =>
    ipcRenderer.invoke('agent:confirm', conversationId, actionIds),

  // OCR — routed through main process to avoid blocking renderer (issue 6a)
  runOCR: (imageBase64: string) => ipcRenderer.invoke('ocr:run', imageBase64),

  // App settings persistence
  getSettings: () => ipcRenderer.invoke('settings:get'),
  setSettings: (settings: Record<string, unknown>) => ipcRenderer.invoke('settings:set', settings),

  // Error forwarding — renderer → main for persistent logging (issue 5a)
  reportError: (context: string, error: string) =>
    ipcRenderer.send('renderer:error', context, error),

  // Navigation (mainWindow view switching) — with cleanup (issue 7c)
  onNavigate: (callback: (view: string) => void) => {
    const handler = (_e: unknown, view: string) => callback(view);
    safeOn('navigate', handler);
  },
  onSplashStatus: (callback: (status: string) => void) => {
    const handler = (_e: unknown, status: string) => callback(status);
    safeOn('splash:status', handler);
  },
  onUserInfo: (callback: (info: { name: string }) => void) => {
    const handler = (_e: unknown, info: { name: string }) => callback(info);
    safeOn('user:info', handler);
  },
});
