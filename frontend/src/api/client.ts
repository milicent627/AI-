const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Stories
  listStories: () => request<{ stories: any[] }>('/stories/'),
  createStory: (data: any) => request<any>('/stories/', { method: 'POST', body: JSON.stringify(data) }),
  getStory: (id: string) => request<any>(`/stories/${id}`),
  updateStory: (id: string, data: any) => request<any>(`/stories/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteStory: (id: string) => request<any>(`/stories/${id}`, { method: 'DELETE' }),

  // Chapters
  listChapters: (storyId: string) => request<{ chapters: any[] }>(`/chapters/${storyId}`),
  getChapter: (storyId: string, chapterId: string) => request<any>(`/chapters/${storyId}/${chapterId}`),
  updateChapter: (storyId: string, chapterId: string, data: any) =>
    request<any>(`/chapters/${storyId}/${chapterId}`, { method: 'PUT', body: JSON.stringify(data) }),
  createBranch: (storyId: string, data: any) =>
    request<any>(`/chapters/${storyId}/branch`, { method: 'POST', body: JSON.stringify(data) }),

  // Continuation (SSE)
  continueStream: (data: any, onChunk: (text: string) => void, onDone: () => void, onError: (err: string) => void) => {
    const controller = new AbortController();
    fetch(`${BASE}/continuation/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: controller.signal,
    }).then(async (res) => {
      const reader = res.body?.getReader();
      if (!reader) { onError('No response body'); return; }
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
            if (content === '[DONE]') { onDone(); return; }
            if (content.startsWith('[ERROR]')) { onError(content.slice(7)); return; }
            onChunk(content);
          }
        }
      }
    }).catch(err => {
      if (err.name !== 'AbortError') onError(err.message);
    });
    return controller;
  },

  polishStream: (data: any, onChunk: (text: string) => void, onDone: () => void, onError: (err: string) => void) => {
    const controller = new AbortController();
    fetch(`${BASE}/continuation/polish-stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: controller.signal,
    }).then(async (res) => {
      const reader = res.body?.getReader();
      if (!reader) { onError('No response body'); return; }
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
            if (content === '[DONE]') { onDone(); return; }
            if (content.startsWith('[ERROR]')) { onError(content.slice(7)); return; }
            onChunk(content);
          }
        }
      }
    }).catch(err => {
      if (err.name !== 'AbortError') onError(err.message);
    });
    return controller;
  },

  // World Book
  listWorldEntries: (storyId: string, category?: string) =>
    request<{ entries: any[] }>(`/world-book/${storyId}${category ? `?category=${category}` : ''}`),
  getWorldEntry: (storyId: string, entryId: string) => request<any>(`/world-book/${storyId}/${entryId}`),
  updateWorldEntry: (storyId: string, entryId: string, data: any) =>
    request<any>(`/world-book/${storyId}/${entryId}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteWorldEntry: (storyId: string, entryId: string) =>
    request<any>(`/world-book/${storyId}/${entryId}`, { method: 'DELETE' }),
  createRelation: (storyId: string, data: any) =>
    request<any>(`/world-book/${storyId}/relations`, { method: 'POST', body: JSON.stringify(data) }),
  deleteRelation: (storyId: string, relationId: string) =>
    request<any>(`/world-book/${storyId}/relations/${relationId}`, { method: 'DELETE' }),
  // World Book AI assistant (SSE)
  assistStream: (storyId: string, messages: { role: string; content: string }[], onChunk: (text: string) => void, onDone: () => void, onError: (err: string) => void) => {
    const controller = new AbortController();
    fetch(`${BASE}/world-book/${storyId}/assist-stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages }),
      signal: controller.signal,
    }).then(async (res) => {
      const reader = res.body?.getReader();
      if (!reader) { onError('No response body'); return; }
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
            if (content === '[DONE]') { onDone(); return; }
            if (content.startsWith('[ERROR]')) { onError(content.slice(7)); return; }
            onChunk(content);
          }
        }
      }
    }).catch(err => {
      if (err.name !== 'AbortError') onError(err.message);
    });
    return controller;
  },

  // Foreshadowing
  listForeshadowings: (storyId: string, status?: string) =>
    request<{ foreshadowings: any[] }>(`/foreshadowing/${storyId}${status ? `?status=${status}` : ''}`),
  createForeshadowing: (storyId: string, data: any) =>
    request<any>(`/foreshadowing/${storyId}`, { method: 'POST', body: JSON.stringify(data) }),
  updateForeshadowing: (storyId: string, fpId: string, data: any) =>
    request<any>(`/foreshadowing/${storyId}/${fpId}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteForeshadowing: (storyId: string, fpId: string) =>
    request<any>(`/foreshadowing/${storyId}/${fpId}`, { method: 'DELETE' }),

  // Summaries
  listSummaries: (storyId: string) => request<{ summaries: any[] }>(`/summaries/${storyId}`),
  generateSummary: (storyId: string, type: string) =>
    request<any>(`/summaries/${storyId}/generate`, { method: 'POST', body: JSON.stringify({ type }) }),
  deleteSummary: (storyId: string, summaryId: string) =>
    request<any>(`/summaries/${storyId}/${summaryId}`, { method: 'DELETE' }),

  // Models
  listModels: () => request<{ models: any[] }>('/models/'),
  createModel: (data: any) => request<any>('/models/', { method: 'POST', body: JSON.stringify(data) }),
  updateModel: (id: string, data: any) => request<any>(`/models/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteModel: (id: string) => request<any>(`/models/${id}`, { method: 'DELETE' }),

  // Prompt Presets
  listPromptPresets: (role?: string) => request<{ presets: any[] }>(`/prompt-presets/${role ? `?role=${role}` : ''}`),
  createPromptPreset: (data: any) => request<any>('/prompt-presets/', { method: 'POST', body: JSON.stringify(data) }),
  updatePromptPreset: (id: string, data: any) => request<any>(`/prompt-presets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePromptPreset: (id: string) => request<any>(`/prompt-presets/${id}`, { method: 'DELETE' }),
  createFragment: (presetId: string, data: any) => request<any>(`/prompt-presets/${presetId}/fragments`, { method: 'POST', body: JSON.stringify(data) }),
  updateFragment: (presetId: string, fragId: string, data: any) => request<any>(`/prompt-presets/${presetId}/fragments/${fragId}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteFragment: (presetId: string, fragId: string) => request<any>(`/prompt-presets/${presetId}/fragments/${fragId}`, { method: 'DELETE' }),
  reorderFragments: (presetId: string, order: string[]) => request<any>(`/prompt-presets/${presetId}/reorder`, { method: 'POST', body: JSON.stringify({ order }) }),
};
