import { useCallback } from "react";

/**
 * Returns a function that reads a fetch Response's Server-Sent-Events body and
 * dispatches each event to the provided handlers. Buffers across reads so a
 * `data:` line split across chunk boundaries still parses correctly.
 *
 * Shared by the Fan and Staff chat widgets so the streaming loop lives in one place.
 */
export function useChatStream() {
  return useCallback(async (res, { onReset, onToken, onProvider, onRoute } = {}) => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let done = false;

    while (!done) {
      const { value, done: readerDone } = await reader.read();
      done = readerDone;
      if (value) buffer += decoder.decode(value, { stream: !done });

      let newlineIdx;
      while ((newlineIdx = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newlineIdx);
        buffer = buffer.slice(newlineIdx + 1);
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.reset) onReset?.();
          if (data.token) onToken?.(data.token);
          if (data.provider) onProvider?.(data.provider);
          if (data.route) onRoute?.(data.route);
        } catch {
          // Partial or malformed SSE line — ignore safely.
        }
      }
    }
  }, []);
}
