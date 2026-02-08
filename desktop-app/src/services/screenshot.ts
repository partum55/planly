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
 * Capture a screenshot on Wayland (GNOME).
 *
 * Strategy order:
 * 1. gnome-screenshot (most reliable on GNOME/Wayland)
 * 2. grim (wlroots-based compositors)
 * 3. Fallback error
 */
export async function captureScreenshot(): Promise<ScreenshotResult> {
  const tmpFile = path.join(os.tmpdir(), `planly-screenshot-${Date.now()}.png`);

  try {
    // Try gnome-screenshot first (works on GNOME + Wayland)
    await execFileAsync('gnome-screenshot', ['-f', tmpFile]);
  } catch {
    try {
      // Try grim (wlroots/sway)
      await execFileAsync('grim', [tmpFile]);
    } catch {
      throw new Error(
        'Screenshot failed. Install gnome-screenshot or grim for Wayland support.'
      );
    }
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
