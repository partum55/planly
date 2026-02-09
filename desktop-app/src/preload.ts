const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('planly', {
  // Config
  getConfig: () => ipcRenderer.invoke('config:get'),

  // Chat window controls
  closeChat: () => ipcRenderer.send('chat:close'),
  resizeChat: (height: number) => ipcRenderer.send('chat:resize', height),
  resetChat: (callback: () => void) => ipcRenderer.on('chat:reset', callback),

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

  // Navigation (mainWindow view switching)
  onNavigate: (callback: (view: string) => void) =>
    ipcRenderer.on('navigate', (_e: unknown, view: string) => callback(view)),
  onSplashStatus: (callback: (status: string) => void) =>
    ipcRenderer.on('splash:status', (_e: unknown, status: string) => callback(status)),
  onUserInfo: (callback: (info: { name: string }) => void) =>
    ipcRenderer.on('user:info', (_e: unknown, info: { name: string }) => callback(info)),
});
