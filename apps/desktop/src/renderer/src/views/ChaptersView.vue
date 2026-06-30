<script setup lang="ts">
import { useRoute } from 'vue-router'
import { ref, onMounted } from 'vue'

const route = useRoute()
const chapters = ref([])

onMounted(async () => {
  chapters.value = await window.novelTradAPI.invoke('chapter:list', route.params.id)
})
</script>

<template>
  <div>
    <h1>Chapitres</h1>
    <p v-if="!chapters.length" class="empty">Aucun chapitre importe.</p>
    <ul>
      <li v-for="ch in chapters" :key="ch.id">{{ ch.title || ch.id }}</li>
    </ul>
  </div>
</template>

<style scoped>
.empty {
  color: var(--text-secondary);
}
</style>
