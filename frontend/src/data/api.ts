const configuredApiUrl = import.meta.env.VITE_API_BASE_URL;

export const API_BASE_URL = (configuredApiUrl || `${window.location.protocol}//${window.location.hostname}:8000`)
  .replace(/\/+$/, '');