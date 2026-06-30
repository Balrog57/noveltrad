import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AppSettings } from '@shared/types/index.js'

export const useSettingsStore = defineStore('settings', () => {
  const data = ref<Partial<AppSettings>>({})
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      data.value = await window.novelTradAPI.invoke('settings:get')
    } finally {
      loading.value = false
    }
  }

  async function set<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    data.value = await window.novelTradAPI.invoke('settings:set', key, value)
  }

  return { data, loading, load, set }
})
