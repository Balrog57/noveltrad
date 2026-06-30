import { createRouter, createWebHashHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  {
    path: "/project/:projectId",
    name: "project",
    component: () => import("../views/ProjectView.vue"),
  },
  {
    path: "/project/:projectId/chapters",
    name: "chapters",
    component: () => import("../views/ChaptersView.vue"),
  },
  {
    path: "/project/:projectId/chapters/:chapterId",
    name: "chapter-editor",
    component: () => import("../views/ChapterEditorView.vue"),
  },
  {
    path: "/project/:projectId/workflow",
    name: "workflow",
    component: () => import("../views/WorkflowView.vue"),
  },
  {
    path: "/project/:projectId/lexicon",
    name: "lexicon",
    component: () => import("../views/LexiconView.vue"),
  },
  {
    path: "/project/:projectId/history",
    name: "history",
    component: () => import("../views/HistoryView.vue"),
  },
  {
    path: "/project/:projectId/history/:chapterId",
    name: "history-chapter",
    component: () => import("../views/HistoryView.vue"),
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("../views/SettingsView.vue"),
  },
  {
    path: "/console",
    name: "console",
    component: () => import("../views/ConsoleView.vue"),
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

/**
 * Garde de navigation : si l'utilisateur tente d'accéder à une route `/project/*`
 * sans projet ouvert, redirige vers la page d'accueil.
 */
router.beforeEach(async (to) => {
  if (to.path.startsWith("/project")) {
    // Import dynamique pour éviter les dépendances circulaires
    const { useProjectStore } = await import("../stores/project");
    if (!useProjectStore().currentProject) {
      return "/";
    }
  }
});

export default router;
