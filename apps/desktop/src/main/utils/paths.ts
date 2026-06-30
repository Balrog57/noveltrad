import path from 'node:path'
import os from 'node:os'

export function expandHome(input: string): string {
  if (input.startsWith('~/') || input.startsWith('~\\')) {
    return path.join(os.homedir(), input.slice(2))
  }
  return input
}

export function getGlobalConfigDir(): string {
  const appData = process.env.APPDATA || path.join(os.homedir(), '.config')
  return path.join(appData, 'NovelTrad')
}
