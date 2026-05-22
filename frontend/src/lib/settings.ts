const DEFAULTS = {
  aiProvider: 'openai',
  apiKey: '',
  apiBaseUrl: '',
  modelName: 'gpt-4o-mini',
  embedProvider: 'local',
  fontSize: 16,
  theme: 'default',
  lineSpacing: 1.8,
}

export type Settings = typeof DEFAULTS

export function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem('free-for-read-settings')
    if (raw) return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch { /* corrupted */ }
  return { ...DEFAULTS }
}

export function saveSettings(settings: Settings) {
  localStorage.setItem('free-for-read-settings', JSON.stringify(settings))
}
