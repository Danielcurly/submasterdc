export const API_BASE = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');

async function fetchAPI(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  const json = await res.json().catch(() => null);

  if (!res.ok || (json && typeof json.success === 'boolean' && json.success === false)) {
    throw new Error(json?.message || json?.detail || res.statusText || 'API Error');
  }

  if (json && typeof json.success === 'boolean' && 'data' in json) {
    return json.data;
  }

  return json;
}

// Config
export const getConfig = () => fetchAPI('/api/config');
export const saveConfig = (config: Record<string, unknown>) =>
  fetchAPI('/api/config', { method: 'PUT', body: JSON.stringify({ config }) });
export const getProviders = () => fetchAPI('/api/ai/providers');
export const getContentTypes = () => fetchAPI('/api/ai/content-types');
export const getVadPresets = () => fetchAPI('/api/config/vad-presets');
export const getSubtitleStyle = () => fetchAPI('/api/config/subtitles');
export const updateSubtitleStyle = (style: Record<string, unknown>) =>
  fetchAPI('/api/config/subtitles', { method: 'PUT', body: JSON.stringify(style) });

// Libraries
export const getLibraries = () => fetchAPI('/api/libraries');
export const getLibraryMediaStats = () => fetchAPI('/api/libraries/media-stats');
export const addLibrary = (data: { name: string; path: string; scan_mode?: string }) =>
  fetchAPI('/api/libraries', { method: 'POST', body: JSON.stringify(data) });
export const updateLibrary = (id: string, data: Record<string, unknown>) =>
  fetchAPI(`/api/libraries/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const deleteLibrary = (id: string) =>
  fetchAPI(`/api/libraries/${id}`, { method: 'DELETE' });
export const browseDirectory = (path: string) =>
  fetchAPI(`/api/libraries/browse?path=${encodeURIComponent(path)}`);
export const updateLibraryStyles = (id: string) =>
  fetchAPI(`/api/libraries/${id}/update-styles`, { method: 'POST' });

// Tasks
export const getTasks = () => fetchAPI('/api/tasks');
export const clearCompleted = () => fetchAPI('/api/tasks/completed', { method: 'DELETE' });
export const retryTask = (id: number) => fetchAPI(`/api/tasks/${id}/retry`, { method: 'POST' });
export const cancelTask = (id: number) => fetchAPI(`/api/tasks/${id}/cancel`, { method: 'POST' });
export const cancelAllTasks = () => fetchAPI(`/api/tasks/cancel_all`, { method: 'POST' });
export const getTaskStats = () => fetchAPI('/api/tasks/stats');

// Scan
export const triggerScan = (libraryPath: string) =>
  fetchAPI('/api/scan', { method: 'POST', body: JSON.stringify({ library_path: libraryPath }) });

// AI
export const testAIConnection = (data: { api_key: string; base_url: string; model: string }) =>
  fetchAPI('/api/ai/test', { method: 'POST', body: JSON.stringify(data) });
export const getAIProviders = () => fetchAPI('/api/ai/providers');
export const getOllamaModels = (baseUrl: string) =>
  fetchAPI(`/api/ai/ollama-models?base_url=${encodeURIComponent(baseUrl)}`);
export const getLanguages = () => fetchAPI('/api/ai/languages');
export const getAIContentTypes = () => fetchAPI('/api/ai/content-types');
export const getAIUsage = () => fetchAPI('/api/ai/usage');
