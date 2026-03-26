/**
 * Electron Main Process
 *
 * 职责:
 * 1. 创建和管理应用窗口
 * 2. 自动启动 Python 后端服务
 * 3. IPC 通信 (系统托盘、通知等)
 * 4. 应用生命周期管理
 */
const { app, BrowserWindow, Menu, Tray, shell, dialog, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');

// ── 配置 ──
const IS_DEV = process.env.NODE_ENV === 'development';
const BACKEND_PORT = 8000;
const FRONTEND_DEV_URL = `http://localhost:3000`;
const BACKEND_DIR = app.isPackaged
  ? path.join(process.resourcesPath, 'backend')
  : path.join(__dirname, '..', '..', 'backend');

let mainWindow = null;
let tray = null;
let backendProcess = null;
let isQuitting = false;

// ── 后端进程管理 ──

/**
 * 检查端口是否可用
 */
function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close();
      resolve(true);
    });
    server.listen(port);
  });
}

/**
 * 等待端口可用 (后端启动完成)
 */
function waitForPort(port, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      const socket = new net.Socket();
      socket.setTimeout(1000);
      socket.once('connect', () => {
        socket.destroy();
        resolve();
      });
      socket.once('error', () => {
        socket.destroy();
        if (Date.now() - start > timeout) {
          reject(new Error(`Timeout waiting for port ${port}`));
        } else {
          setTimeout(check, 500);
        }
      });
      socket.once('timeout', () => {
        socket.destroy();
        setTimeout(check, 500);
      });
      socket.connect(port, '127.0.0.1');
    };
    check();
  });
}

/**
 * 启动 Python 后端
 */
async function startBackend() {
  const portAvailable = await isPortAvailable(BACKEND_PORT);

  if (!portAvailable) {
    console.log(`Backend already running on port ${BACKEND_PORT}`);
    return;
  }

  console.log('Starting Python backend...');

  // 尝试不同的 Python 命令
  const pythonCommands = ['python3', 'python'];
  let pythonCmd = 'python3';

  for (const cmd of pythonCommands) {
    try {
      const test = spawn(cmd, ['--version']);
      await new Promise((resolve, reject) => {
        test.on('close', (code) => code === 0 ? resolve() : reject());
        test.on('error', reject);
      });
      pythonCmd = cmd;
      break;
    } catch {
      continue;
    }
  }

  backendProcess = spawn(
    pythonCmd,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)],
    {
      cwd: BACKEND_DIR,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
      stdio: ['pipe', 'pipe', 'pipe'],
    }
  );

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend:', err.message);
    dialog.showErrorBox(
      'Backend Error',
      `Failed to start Python backend: ${err.message}\n\nPlease ensure Python is installed and dependencies are installed:\ncd backend && pip install -r requirements.txt`
    );
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend process exited with code ${code}`);
    if (!isQuitting && code !== 0) {
      dialog.showErrorBox('Backend Crashed', `Backend process exited with code ${code}`);
    }
    backendProcess = null;
  });

  // 等待后端启动完成
  try {
    await waitForPort(BACKEND_PORT, 30000);
    console.log('Backend started successfully');
  } catch {
    console.error('Backend failed to start within 30 seconds');
  }
}

/**
 * 停止后端
 */
function stopBackend() {
  if (backendProcess) {
    console.log('Stopping backend...');
    backendProcess.kill('SIGTERM');
    // 强制 kill 如果 5 秒后还没退出
    setTimeout(() => {
      if (backendProcess) {
        backendProcess.kill('SIGKILL');
      }
    }, 5000);
  }
}

// ── 窗口管理 ──

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: 'QuantTrader',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    trafficLightPosition: { x: 15, y: 15 },
    backgroundColor: '#0f1117',
    show: false, // 等加载完再显示, 避免白屏
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // 加载页面
  if (IS_DEV) {
    mainWindow.loadURL(FRONTEND_DEV_URL);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  // 准备好后显示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // 关闭时隐藏到托盘 (macOS 习惯)
  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 外部链接在浏览器打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// ── 菜单 ──

function createMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{
      label: 'QuantTrader',
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { label: 'Quit', accelerator: 'Cmd+Q', click: () => { isQuitting = true; app.quit(); } },
      ]
    }] : []),
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ]
    },
    {
      label: 'Trading',
      submenu: [
        { label: 'Dashboard', accelerator: 'CmdOrCtrl+1', click: () => navigateTo('/') },
        { label: 'Strategies', accelerator: 'CmdOrCtrl+2', click: () => navigateTo('/strategies') },
        { label: 'Factors', accelerator: 'CmdOrCtrl+3', click: () => navigateTo('/factors') },
        { label: 'Backtest', accelerator: 'CmdOrCtrl+4', click: () => navigateTo('/backtest') },
        { label: 'Trading', accelerator: 'CmdOrCtrl+5', click: () => navigateTo('/trading') },
      ]
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        ...(isMac ? [{ type: 'separator' }, { role: 'front' }] : [{ role: 'close' }]),
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'API Documentation',
          click: () => shell.openExternal(`http://localhost:${BACKEND_PORT}/docs`),
        },
        {
          label: 'Backend Status',
          click: async () => {
            try {
              const resp = await fetch(`http://localhost:${BACKEND_PORT}/health`);
              const data = await resp.json();
              dialog.showMessageBox({
                type: 'info',
                title: 'Backend Status',
                message: `Status: ${data.status}\nPort: ${BACKEND_PORT}\nPID: ${backendProcess?.pid || 'external'}`,
              });
            } catch {
              dialog.showMessageBox({
                type: 'warning',
                title: 'Backend Status',
                message: 'Backend is not responding',
              });
            }
          }
        },
      ]
    }
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function navigateTo(path) {
  if (mainWindow) {
    mainWindow.webContents.executeJavaScript(
      `window.location.hash = ''; window.history.pushState({}, '', '${path}'); window.dispatchEvent(new PopStateEvent('popstate'));`
    );
  }
}

// ── IPC 处理 ──

ipcMain.handle('get-backend-status', async () => {
  try {
    const resp = await fetch(`http://localhost:${BACKEND_PORT}/health`);
    return { running: true, data: await resp.json() };
  } catch {
    return { running: false };
  }
});

ipcMain.handle('get-app-info', () => ({
  version: app.getVersion(),
  platform: process.platform,
  arch: process.arch,
  isDev: IS_DEV,
  backendPort: BACKEND_PORT,
}));

// ── 应用生命周期 ──

app.whenReady().then(async () => {
  // 启动后端
  await startBackend();

  // 创建窗口
  createWindow();
  createMenu();

  // macOS: 点击 dock 图标重新显示窗口
  app.on('activate', () => {
    if (mainWindow) {
      mainWindow.show();
    } else {
      createWindow();
    }
  });
});

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('will-quit', () => {
  stopBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
