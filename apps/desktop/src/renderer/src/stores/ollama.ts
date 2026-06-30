import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { OllamaModelInfo } from '@shared/types/index.js'

export const useOllamaStore = defineStore('ollama', () => {
  const available = ref(false)
  const models = ref<OllamaModelInfo[]>([])
  const loading = ref(false)

  async function check(host?: string) {
    loading.value = true
    try {
      if (host) {
        await window.novelTradAPI.invoke('settings:set', 'ollamaHost', host)
      }
      available.value = await window.novelTradAPI.invoke('ollama:is-available')
      if (available.value) {
        models.value = await window.novelTradAPI.invoke('ollama:list-models')
      }
    } finally {
      loading.value = false
    }
  }

  return { available, models, loading, check }
})
