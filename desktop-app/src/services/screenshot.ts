import { execFile } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

const execFileAsync = promisify(execFile);

export interface ScreenshotResult {
  imageBase64: string;
  timestamp: string;
}

/**
 * Capture a screenshot on the current platform.
 *
 * - Linux:   gnome-screenshot → grim fallback
 * - macOS:   screencapture -x (silent, built-in)
 * - Windows: PowerShell + System.Drawing (no external tools)
 */
export async function captureScreenshot(): Promise<ScreenshotResult> {
  const tmpFile = path.join(os.tmpdir(), `planly-screenshot-${Date.now()}.png`);

  switch (process.platform) {
    case 'linux':
      await captureLinux(tmpFile);
      break;
    case 'darwin':
      await captureMacOS(tmpFile);
      break;
    case 'win32':
      await captureWindows(tmpFile);
      break;
    default:
      throw new Error(`Unsupported platform: ${process.platform}`);
  }

  const imageBuffer = await fs.promises.readFile(tmpFile);
  const imageBase64 = imageBuffer.toString('base64');

  // Clean up temp file
  await fs.promises.unlink(tmpFile).catch(() => {});

  return {
    imageBase64,
    timestamp: new Date().toISOString(),
  };
}

async function captureLinux(tmpFile: string): Promise<void> {
  try {
    await execFileAsync('gnome-screenshot', ['-f', tmpFile]);
  } catch {
    try {
      await execFileAsync('grim', [tmpFile]);
    } catch {
      throw new Error(
        'Screenshot failed. Install gnome-screenshot or grim for Wayland support.'
      );
    }
  }
}

async function captureMacOS(tmpFile: string): Promise<void> {
  try {
    await execFileAsync('screencapture', ['-x', tmpFile]);
  } catch {
    throw new Error('Screenshot failed. screencapture is not available.');
  }
}

async function captureWindows(tmpFile: string): Promise<void> {
  const psScript = `
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save('${tmpFile.replace(/\\/g, '\\\\')}')
$graphics.Dispose()
$bitmap.Dispose()
`.trim();

  try {
    await execFileAsync('powershell', [
      '-NoProfile',
      '-NonInteractive',
      '-Command',
      psScript,
    ]);
  } catch {
    throw new Error('Screenshot failed. PowerShell screenshot capture is not available.');
  }
}
