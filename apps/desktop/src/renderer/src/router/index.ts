import { createRouter, createWebHashHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";

// v3 : 3 routes seulement (Dashboard, Project all-in-one, Settings).
// Les anciennes routes (chapters, chapter-editor, workflow, lexicon, history,
// console, plugins, help) ont été supprimées avec leurs vues.
const routes = [
  { path: "/", name: "home", component: HomeView },
  {
    path: "/project/:projectId",
    name: "project",
    component: () => import("../views/ProjectView.vue"),
  },
  {
    path: "/settings",
    name: "settings",
    component: () => import("../views/SettingsView.vue"),
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
    const { useProjectStore } = await import("../stores/project");
    if (!useProjectStore().currentProject) {
      return "/";
    }
  }
});

export default router;
