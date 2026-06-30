<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const links = [
  { name: 'home', label: 'Accueil', icon: '🏠' },
  { name: 'settings', label: 'Paramètres', icon: '⚙️' }
]

function isActive(name: string) {
  return route.name === name
}
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <h1>NovelTrad</h1>
    </div>
    <nav class="nav">
      <button
        v-for="link in links"
        :key="link.name"
        class="nav-item"
        :class="{ active: isActive(link.name) }"
        @click="router.push({ name: link.name })"
      >
        <span class="icon">{{ link.icon }}</span>
        <span>{{ link.label }}</span>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  background-color: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.brand {
  padding-bottom: 24px;
  border-bottom: 1px solid var(--bg-tertiary);
  margin-bottom: 16px;
}

.brand h1 {
  margin: 0;
  font-size: 20px;
  color: var(--accent);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--border-radius);
  border: none;
  background: transparent;
  color: var(--text-secondary);
  text-align: left;
}

.nav-item:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item.active {
  background-color: var(--bg-tertiary);
  color: var(--accent);
  border-left: 3px solid var(--accent);
}

.icon {
  font-size: 18px;
}
</style>
