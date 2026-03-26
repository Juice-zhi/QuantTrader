/**
 * Electron Preload Script
 *
 * 安全地暴露有限的 API 给 Renderer Process (React)
 * 通过 contextBridge 确保安全性
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // 获取后端状态
  getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),

  // 获取应用信息
  getAppInfo: () => ipcRenderer.invoke('get-app-info'),

  // 平台检测
  platform: process.platform,

  // 版本
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
});
