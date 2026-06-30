<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { ref, onMounted } from "vue";
import { useProjectStore } from "../stores/project";
import { useWorkflowStore } from "../stores/workflow";
import ExportDialog from "../components/export/ExportDialog.vue";
import type { Chapter } from "@shared/types/index.js";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const workflowStore = useWorkflowStore();
const chapters = ref<Chapter[]>([]);
const translatingId = ref<string | null>(null);
const exportChapterId = ref<string | null>(null);

const projectId = (route.params.projectId as string) || "";

onMounted(async () => {
  chapters.value = await window.novelTradAPI.invoke("chapter:list", projectId);
  projectStore.chapters = chapters.value;
});

/** Naviguer vers l'éditeur pour un chapitre */
function openEditor(chapter: Chapter): void {
  router.push({
    name: "chapter-editor",
    params: { projectId, chapterId: chapter.id },
  });
}

async function translateChapter(chapter: Chapter) {
  if (!projectId) return;
  const projectPath = await window.novelTradAPI.invoke<string>(
    "project:path",
    projectId,
  );
  translatingId.value = chapter.id;
  try {
    await workflowStore.start(projectPath, chapter.id);
  } finally {
    translatingId.value = null;
  }
}

function progressFor(chapterId: string): string {
  if (workflowStore.progress?.chapterId !== chapterId) return "";
  const { step, totalSteps } = workflowStore.progress;
  return `${step.name} (${step.orderIndex + 1}/${totalSteps})`;
}
</script>

<template>
  <div>
    <h1>Chapitres</h1>
    <p v-if="!chapters.length" class="empty">Aucun chapitre importé.</p>
    <ul class="chapter-list">
      <li v-for="ch in chapters" :key="ch.id" class="chapter-item">
        <div
          class="chapter-info"
          @click="openEditor(ch)"
          role="button"
          tabindex="0"
          @keydown.enter="openEditor(ch)"
        >
          <strong>{{ ch.title || ch.id }}</strong>
          <span class="badge" :class="ch.status">{{ ch.status }}</span>
        </div>
        <div class="chapter-actions">
          <button
            class="btn-primary"
            :disabled="translatingId === ch.id || workflowStore.loading"
            @click="translateChapter(ch)"
          >
            Traduire
          </button>
          <button class="btn-primary" @click="exportChapterId = ch.id">
            Exporter
          </button>
          <span v-if="progressFor(ch.id)" class="progress">{{
            progressFor(ch.id)
          }}</span>
        </div>
      </li>
    </ul>

    <!-- Dialogue d'export -->
    <ExportDialog
      :visible="exportChapterId !== null"
      :chapter-id="exportChapterId"
      @close="exportChapterId = null"
    />
  </div>
</template>

<style scoped>
.empty {
  color: var(--text-secondary);
}

.chapter-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chapter-item {
  background-color: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chapter-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
}

.chapter-info:hover strong {
  color: var(--accent);
}

.chapter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background-color: var(--bg-tertiary);
  text-transform: uppercase;
}

.badge.completed {
  background-color: var(--success);
  color: white;
}

.progress {
  color: var(--text-secondary);
  font-size: 13px;
}

.btn-primary {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: var(--border-radius);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
