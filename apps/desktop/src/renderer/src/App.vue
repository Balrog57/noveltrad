<script setup lang="ts">
import { onMounted } from "vue";
import { useSettingsStore } from "./stores/settings";
import Sidebar from "./components/Sidebar.vue";

const settings = useSettingsStore();

onMounted(async () => {
  await settings.load();
});
</script>

<template>
  <div class="app-layout">
    <Sidebar />
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-main {
  flex: 1;
  overflow: auto;
  padding: 24px;
}
</style>
