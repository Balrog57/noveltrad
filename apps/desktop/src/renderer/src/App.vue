<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useSettingsStore } from "./stores/settings";
import Sidebar from "./components/Sidebar.vue";
import WizardDialog from "./components/wizard/WizardDialog.vue";

const settings = useSettingsStore();
const router = useRouter();
const showWizard = ref(false);

onMounted(async () => {
  await settings.load();
  // SDD §4.18 : afficher le wizard au premier lancement
  if (settings.data.firstRunCompleted === false) {
    showWizard.value = true;
  }

  // Écoute les événements du menu natif
  window.novelTradAPI.on("navigate", (route: unknown) => {
    if (typeof route === "string") router.push(route);
  });
  window.novelTradAPI.on("menu", (action: unknown) => {
    if (action === "open-project") {
      // Ouvre le dialogue de sélection de dossier (via IPC)
      window.novelTradAPI.invoke("project:open-dialog").catch(() => {});
    }
  });
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
