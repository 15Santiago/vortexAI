const configuredAssistantApiUrl = import.meta.env.VITE_ASSISTANT_API_URL;

export const ASSISTANT_API_URL = (
  configuredAssistantApiUrl || `${window.location.protocol}//${window.location.hostname}:8001`
).replace(/\/+$/, '');

export const ASSISTANT_ACCESS_CODE = import.meta.env.VITE_ASSISTANT_ACCESS_CODE || '';
