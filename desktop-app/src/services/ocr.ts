import Tesseract from 'tesseract.js';

export interface ParsedMessage {
  username: string;
  text: string;
  timestamp: string;
}

export interface OcrResult {
  rawText: string;
  confidence: number;
  messages: ParsedMessage[];
}

/**
 * Extract text from a screenshot image using Tesseract OCR,
 * then parse into structured chat messages.
 */
export async function extractFromImage(imageBase64: string): Promise<OcrResult> {
  const imageBuffer = Buffer.from(imageBase64, 'base64');

  const { data } = await Tesseract.recognize(imageBuffer, 'eng', {
    logger: (info) => {
      if (info.status === 'recognizing text' && typeof info.progress === 'number') {
        // Progress available for UI feedback if needed
      }
    },
  });

  const rawText = data.text;
  const confidence = data.confidence;

  const messages = parseMessages(rawText);

  return { rawText, confidence, messages };
}

// ─── Generic multi-app message parser ───────────────────────

/**
 * Attempts to parse chat messages from OCR text using multiple
 * heuristics for different chat app formats.
 *
 * Supported patterns:
 *  - "Username: message text" (generic)
 *  - "Username\nTimestamp\nMessage text" (Discord-like)
 *  - "[HH:MM] Username: message" (IRC/Matrix-like)
 *  - "Username, HH:MM PM: message" (WhatsApp-like)
 */
function parseMessages(text: string): ParsedMessage[] {
  const lines = text.split('\n').filter((l) => l.trim().length > 0);

  // Try each parser strategy, return the one that extracts the most messages
  const strategies = [
    parseColonSeparated,
    parseTimestampBracket,
    parseWhatsAppStyle,
    parseDiscordStyle,
  ];

  let bestResult: ParsedMessage[] = [];

  for (const strategy of strategies) {
    const result = strategy(lines);
    if (result.length > bestResult.length) {
      bestResult = result;
    }
  }

  // Fallback: if no parser found messages, treat whole text as a single block
  if (bestResult.length === 0 && text.trim().length > 0) {
    bestResult = [
      {
        username: 'Unknown',
        text: text.trim(),
        timestamp: new Date().toISOString(),
      },
    ];
  }

  return bestResult;
}

/**
 * Pattern: "Username: message text"
 */
function parseColonSeparated(lines: string[]): ParsedMessage[] {
  const messages: ParsedMessage[] = [];
  const pattern = /^([A-Za-z0-9_\s]{2,20}):\s+(.+)$/;

  for (const line of lines) {
    const match = line.match(pattern);
    if (match) {
      messages.push({
        username: match[1].trim(),
        text: match[2].trim(),
        timestamp: new Date().toISOString(),
      });
    }
  }

  return messages;
}

/**
 * Pattern: "[HH:MM] Username: message" (IRC/Matrix)
 */
function parseTimestampBracket(lines: string[]): ParsedMessage[] {
  const messages: ParsedMessage[] = [];
  const pattern = /^\[(\d{1,2}:\d{2}(?:\s*[APap][Mm])?)\]\s+([A-Za-z0-9_]+):\s+(.+)$/;

  for (const line of lines) {
    const match = line.match(pattern);
    if (match) {
      messages.push({
        username: match[2].trim(),
        text: match[3].trim(),
        timestamp: match[1].trim(),
      });
    }
  }

  return messages;
}

/**
 * Pattern: "Username, HH:MM PM: message" (WhatsApp)
 */
function parseWhatsAppStyle(lines: string[]): ParsedMessage[] {
  const messages: ParsedMessage[] = [];
  const pattern =
    /^([A-Za-z0-9_\s]+),\s*(\d{1,2}:\d{2}\s*[APap][Mm]):\s+(.+)$/;

  for (const line of lines) {
    const match = line.match(pattern);
    if (match) {
      messages.push({
        username: match[1].trim(),
        text: match[3].trim(),
        timestamp: match[2].trim(),
      });
    }
  }

  return messages;
}

/**
 * Pattern: Discord-like (Username on one line, timestamp on next, message on next)
 */
function parseDiscordStyle(lines: string[]): ParsedMessage[] {
  const messages: ParsedMessage[] = [];
  const usernamePattern = /^[A-Za-z0-9_]{2,20}$/;
  const timestampPattern = /^\d{1,2}:\d{2}\s*(?:[APap][Mm])?/;

  let i = 0;
  while (i < lines.length - 1) {
    const maybeName = lines[i].trim();
    if (usernamePattern.test(maybeName)) {
      // Check if next line is a timestamp
      const nextLine = lines[i + 1].trim();
      if (timestampPattern.test(nextLine) && i + 2 < lines.length) {
        // Collect message lines until next username
        const textLines: string[] = [];
        let j = i + 2;
        while (j < lines.length && !usernamePattern.test(lines[j].trim())) {
          if (!timestampPattern.test(lines[j].trim())) {
            textLines.push(lines[j].trim());
          }
          j++;
        }
        if (textLines.length > 0) {
          messages.push({
            username: maybeName,
            text: textLines.join(' '),
            timestamp: nextLine,
          });
        }
        i = j;
        continue;
      }
    }
    i++;
  }

  return messages;
}
