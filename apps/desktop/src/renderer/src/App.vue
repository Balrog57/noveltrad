<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useSettingsStore } from "./stores/settings";
import { useUpdateStore } from "./stores/update";
import Sidebar from "./components/Sidebar.vue";
import WizardDialog from "./components/wizard/WizardDialog.vue";

const settings = useSettingsStore();
const router = useRouter();
const showWizard = ref(false);

// Instancier le store update le plus tôt possible pour ne pas manquer
// l'événement update:available du check automatique au démarrage (main → 5s).
// useUpdateStore() enregistre les listeners IPC dans son setup.
const _updateStore = useUpdateStore();

onMounted(async () => {
  await settings.load();
  if (import.meta.env.DEV) {
    console.log("[App] Settings loaded:", JSON.stringify(settings.data));
  }
  // SDD §4.18 : afficher le wizard au premier lancement
  if (settings.data.firstRunCompleted === false) {
    showWizard.value = true;
  }

  // Écoute les événements du menu natif
  window.novelTradAPI.on("navigate", (route: unknown) => {
    if (typeof route === "string") {router.push(route);}
  });
  window.novelTradAPI.on("menu", async (action: unknown) => {
    if (action === "open-project") {
      try {
        const project = await window.novelTradAPI.invoke<{ id: string } | null>("project:open-dialog");
        if (project?.id) {
          router.push({ name: "project", params: { projectId: project.id } });
        }
      } catch {
        // L'utilisateur a annulé le dialogue
      }
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
