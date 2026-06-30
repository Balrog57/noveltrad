export const IPC_CHANNELS = [
  'project:create',
  'project:open',
  'project:list-recent',
  'project:delete',
  'ollama:list-models',
  'ollama:pull-model',
  'ollama:is-available',
  'settings:get',
  'settings:set',
  'workflow:start',
  'workflow:pause',
  'workflow:resume',
  'workflow:retry-step',
  'lexicon:list',
  'lexicon:save',
  'chapter:list',
  'chapter:import',
  'export:run',
  'dialog:open-file'
] as const

export type IpcChannel = (typeof IPC_CHANNELS)[number]

