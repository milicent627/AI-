import { useState, useRef, useCallback } from 'react';

interface SSEState {
  isStreaming: boolean;
  content: string;
  error: string | null;
}

export function useSSEStream() {
  const [state, setState] = useState<SSEState>({
    isStreaming: false,
    content: '',
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (url: string, body: unknown) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ isStreaming: true, content: '', error: null });

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      const reader = res.body?.getReader();
      if (!reader) {
        setState(s => ({ ...s, isStreaming: false, error: 'No response body' }));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.slice(6);
            if (content === '[DONE]') {
              setState(s => ({ ...s, isStreaming: false }));
              return;
            }
            if (content.startsWith('[ERROR]')) {
              setState(s => ({ ...s, isStreaming: false, error: content.slice(7) }));
              return;
            }
            setState(s => ({ ...s, content: s.content + content }));
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      setState(s => ({
        ...s,
        isStreaming: false,
        error: err instanceof Error ? err.message : String(err),
      }));
    }
  }, []);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState(s => ({ ...s, isStreaming: false }));
  }, []);

  return { ...state, start, abort };
}
