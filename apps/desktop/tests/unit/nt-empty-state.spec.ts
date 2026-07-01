// @vitest-environment happy-dom
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import NtEmptyState from "../../src/renderer/src/components/ui/NtEmptyState.vue";

describe("NtEmptyState", () => {
  it("devrait afficher le titre et l'icone", () => {
    const wrapper = mount(NtEmptyState, {
      props: { icon: "📖", title: "Aucun projet" },
    });
    expect(wrapper.text()).toContain("📖");
    expect(wrapper.text()).toContain("Aucun projet");
  });

  it("devrait afficher la description optionnelle", () => {
    const wrapper = mount(NtEmptyState, {
      props: {
        icon: "📖",
        title: "Vide",
        description: "Créez votre premier projet.",
      },
    });
    expect(wrapper.text()).toContain("Créez votre premier projet.");
  });

  it("devrait afficher un bouton si actionLabel est fourni", () => {
    const wrapper = mount(NtEmptyState, {
      props: {
        icon: "📖",
        title: "Vide",
        actionLabel: "Créer",
      },
    });
    const btn = wrapper.find("button");
    expect(btn.exists()).toBe(true);
    expect(btn.text()).toBe("Créer");
  });

  it("devrait emettre action quand le bouton est clique", async () => {
    const wrapper = mount(NtEmptyState, {
      props: {
        icon: "📖",
        title: "Vide",
        actionLabel: "Action",
      },
    });
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("action")).toHaveLength(1);
  });

  it("ne devrait pas afficher de bouton sans actionLabel", () => {
    const wrapper = mount(NtEmptyState, {
      props: { icon: "📖", title: "Vide" },
    });
    expect(wrapper.find("button").exists()).toBe(false);
  });
});
