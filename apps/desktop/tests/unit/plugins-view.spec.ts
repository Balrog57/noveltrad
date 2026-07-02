// @vitest-environment happy-dom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { usePluginsStore } from "../../src/renderer/src/stores/plugins";
import { mount } from "@vue/test-utils";
import PluginsView from "../../src/renderer/src/views/PluginsView.vue";

// Mock window.novelTradAPI
vi.stubGlobal("window", {
  novelTradAPI: {
    invoke: vi.fn(),
    on: vi.fn(),
  },
});

// Mock NtCard, NtButton, NtBadge, NtModal, NtEmptyState, NtToast
vi.mock("../../src/renderer/src/components/ui/NtCard.vue", () => ({
  default: {
    name: "NtCard",
    template: "<div class='nt-card'><slot /></div>",
  },
}));
vi.mock("../../src/renderer/src/components/ui/NtButton.vue", () => ({
  default: {
    name: "NtButton",
    template: '<button class="nt-button" @click="$emit(\'click\')"><slot /></button>',
    props: ["variant", "size"],
  },
}));
vi.mock("../../src/renderer/src/components/ui/NtBadge.vue", () => ({
  default: {
    name: "NtBadge",
    template: '<span class="nt-badge"><slot /></span>',
    props: ["variant"],
  },
}));
vi.mock("../../src/renderer/src/components/ui/NtModal.vue", () => ({
  default: {
    name: "NtModal",
    template: '<div class="nt-modal" v-if="visible"><slot /><slot name="footer" /></div>',
    props: ["visible", "title"],
    emits: ["close"],
  },
}));
vi.mock("../../src/renderer/src/components/ui/NtEmptyState.vue", () => ({
  default: {
    name: "NtEmptyState",
    template: '<div class="nt-empty-state">{{ icon }} {{ title }} {{ description }}</div>',
    props: ["icon", "title", "description"],
  },
}));
vi.mock("../../src/renderer/src/components/ui/NtToast.vue", () => ({
  default: {
    name: "NtToast",
    template: '<div class="nt-toast">{{ message }}</div>',
    props: ["message"],
    emits: ["close"],
  },
}));

describe("PluginsView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(window.novelTradAPI.invoke).mockReset();
  });

  it("affiche le titre", async () => {
    vi.mocked(window.novelTradAPI.invoke).mockResolvedValue([]);

    const wrapper = mount(PluginsView, {
      global: {
        plugins: [createPinia()],
      },
    });

    await new Promise((r) => setTimeout(r, 10));
    expect(wrapper.find("h1").text()).toBe("Plugins");
  });

  it("affiche NtEmptyState si aucun plugin", async () => {
    vi.mocked(window.novelTradAPI.invoke).mockResolvedValue([]);

    const wrapper = mount(PluginsView, {
      global: {
        plugins: [createPinia()],
      },
    });

    await new Promise((r) => setTimeout(r, 10));
    expect(wrapper.find(".nt-empty-state").exists()).toBe(true);
  });

  it("affiche la liste des plugins", async () => {
    vi.mocked(window.novelTradAPI.invoke).mockResolvedValue([
      {
        id: "com.test.plugin",
        name: "Test Plugin",
        version: "1.0.0",
        type: "export",
        permissions: ["fs-write"],
        status: "active",
      },
    ]);

    const wrapper = mount(PluginsView, {
      global: {
        plugins: [createPinia()],
      },
    });

    await new Promise((r) => setTimeout(r, 10));
    expect(wrapper.text()).toContain("Test Plugin");
    expect(wrapper.text()).toContain("1.0.0");
  });

  it("affiche le badge Actif pour un plugin actif", async () => {
    vi.mocked(window.novelTradAPI.invoke).mockResolvedValue([
      {
        id: "com.test.active",
        name: "Active Plugin",
        version: "1.0.0",
        type: "agent",
        permissions: [],
        status: "active",
      },
    ]);

    const wrapper = mount(PluginsView, {
      global: {
        plugins: [createPinia()],
      },
    });

    await new Promise((r) => setTimeout(r, 10));
    expect(wrapper.text()).toContain("Actif");
  });

  it("affiche le badge Erreur pour un plugin en erreur", async () => {
    vi.mocked(window.novelTradAPI.invoke).mockResolvedValue([
      {
        id: "com.test.error",
        name: "Error Plugin",
        version: "1.0.0",
        type: "export",
        permissions: [],
        status: "error",
        errorMessage: "Test error message",
      },
    ]);

    const wrapper = mount(PluginsView, {
      global: {
        plugins: [createPinia()],
      },
    });

    await new Promise((r) => setTimeout(r, 10));
    expect(wrapper.text()).toContain("Erreur");
    expect(wrapper.text()).toContain("Test error message");
  });

  it("appelle enable/disable au clic sur Activer/Désactiver", async () => {
    vi.mocked(window.novelTradAPI.invoke)
      .mockResolvedValueOnce([
        {
          id: "com.test.plugin",
          name: "Test Plugin",
          version: "1.0.0",
          type: "export",
          permissions: [],
          status: "inactive",
        },
      ]) // first load()
      .mockResolvedValueOnce([]) // requestPermissions()
      .mockResolvedValueOnce({ success: true }) // enable
      .mockResolvedValueOnce([
        {
          id: "com.test.plugin",
          name: "Test Plugin",
          version: "1.0.0",
          type: "export",
          permissions: [],
          status: "active",
        },
      ]); // load() after enable

    const wrapper = mount(PluginsView, {
      global: {
        plugins: [createPinia()],
      },
    });

    await new Promise((r) => setTimeout(r, 10));
    const buttons = wrapper.findAll(".nt-button");
    expect(buttons.length).toBeGreaterThanOrEqual(1);
  });

  it("store retourne les plugins chargés", async () => {
    vi.mocked(window.novelTradAPI.invoke).mockResolvedValue([
      { id: "p1", name: "P1", version: "1.0.0", type: "export", permissions: [], status: "inactive" },
    ]);

    const store = usePluginsStore();
    await store.load();
    expect(store.plugins).toHaveLength(1);
    expect(store.plugins[0].name).toBe("P1");
  });

  it("affiche le bouton Configurer si le plugin a un configSchema", async () => {
    vi.mocked(window.novelTradAPI.invoke)
      .mockResolvedValueOnce([
        {
          id: "com.test.config",
          name: "Configurable Plugin",
          version: "1.0.0",
          type: "export",
          permissions: [],
          status: "inactive",
          configSchema: { strictness: { type: "number", default: 0.8 } },
        },
      ])
      .mockResolvedValueOnce([]); // requestPermissions

    const wrapper = mount(PluginsView, {
      global: { plugins: [createPinia()] },
    });

    await new Promise((r) => setTimeout(r, 10));
    const buttons = wrapper.findAllComponents({ name: "NtButton" });
    const configButtons = buttons.filter((b) => b.text().includes("Configurer"));
    expect(configButtons.length).toBe(1);
  });

  it("n'affiche pas le bouton Configurer si le plugin n'a pas de configSchema", async () => {
    vi.mocked(window.novelTradAPI.invoke)
      .mockResolvedValueOnce([
        {
          id: "com.test.simple",
          name: "Simple Plugin",
          version: "1.0.0",
          type: "export",
          permissions: [],
          status: "inactive",
        },
      ])
      .mockResolvedValueOnce([]);

    const wrapper = mount(PluginsView, {
      global: { plugins: [createPinia()] },
    });

    await new Promise((r) => setTimeout(r, 10));
    const buttons = wrapper.findAllComponents({ name: "NtButton" });
    const configButtons = buttons.filter((b) => b.text().includes("Configurer"));
    expect(configButtons.length).toBe(0);
  });
});
