/**
 * Electron API 类型声明
 */
export {};

declare global {
  interface Window {
    electronAPI?: {
      getBackendStatus: () => Promise<{ running: boolean; data?: any }>;
      getAppInfo: () => Promise<{
        version: string;
        platform: string;
        arch: string;
        isDev: boolean;
        backendPort: number;
      }>;
      platform: string;
      versions: {
        node: string;
        chrome: string;
        electron: string;
      };
    };
  }
}
