<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useSettingsStore } from "./stores/settings";
import Sidebar from "./components/Sidebar.vue";
import WizardDialog from "./components/wizard/WizardDialog.vue";

const settings = useSettingsStore();
const showWizard = ref(false);

onMounted(async () => {
  await settings.load();
  // SDD §4.18 : afficher le wizard au premier lancement
  if (settings.data.firstRunCompleted === false) {
    showWizard.value = true;
  }
});

function onWizardClose(): void {
  showWizard.value = false;
}
</script>

<template>
  <div class="app-layout">
    <Sidebar />
    <main class="app-main">
      <router-view />
    </main>
    <WizardDialog v-if="showWizard" @close="onWizardClose" />
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
