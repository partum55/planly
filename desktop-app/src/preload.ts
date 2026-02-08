const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('planly', {
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

  // Legacy (login window controls)
  onLoginSuccess: (tokens: { access_token: string; refresh_token: string }) =>
    ipcRenderer.send('login:success', tokens),
  closeLogin: () => ipcRenderer.send('login:close'),
  skipLogin: () => ipcRenderer.send('login:skip'),

  // Start window
  onStartStatus: (callback: (status: string) => void) =>
    ipcRenderer.on('start:status', (_e: unknown, status: string) => callback(status)),
});
