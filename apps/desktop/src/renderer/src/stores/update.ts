import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface UpdateProgress {
  percent: number
  bytesPerSecond: number
  total: number
  transferred: number
}

export interface UpdatePayload {
  version?: string
  releaseDate?: string
  releaseNotes?: string
  message?: string
  progress?: UpdateProgress
}

export const useUpdateStore = defineStore('update', () => {
  const available = ref(false)
  const downloaded = ref(false)
  const progress = ref<UpdateProgress | null>(null)
  const error = ref<string | null>(null)
  const info = ref<UpdatePayload | null>(null)

  window.novelTradAPI.on('update:available', (payload: unknown) => {
    available.value = true
    info.value = payload as UpdatePayload
  })

  window.novelTradAPI.on('update:downloaded', () => {
    downloaded.value = true
  })

  window.novelTradAPI.on('update:progress', (payload: unknown) => {
    progress.value = (payload as { percent: number; bytesPerSecond: number; total: number; transferred: number }) ?? null
  })

  window.novelTradAPI.on('update:error', (payload: unknown) => {
    error.value = (payload as { message: string }).message
  })

  async function check(): Promise<void> {
    await window.novelTradAPI.invoke('update:check')
  }

  async function download(): Promise<void> {
    await window.novelTradAPI.invoke('update:download')
  }

  async function install(): Promise<void> {
    await window.novelTradAPI.invoke('update:install')
  }

  async function setChannel(channel: 'latest' | 'beta' | 'alpha'): Promise<void> {
    await window.novelTradAPI.invoke('update:set-channel', channel)
  }

  return { available, downloaded, progress, error, info, check, download, install, setChannel }
})
