// @vitest-environment happy-dom
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import NtTooltip from "../../src/renderer/src/components/ui/NtTooltip.vue";

describe("NtTooltip", () => {
  it("devrait afficher le texte du tooltip", () => {
    const wrapper = mount(NtTooltip, {
      props: { text: "Aide" },
      slots: { default: "?" },
    });
    expect(wrapper.text()).toContain("Aide");
    expect(wrapper.text()).toContain("?");
  });

  it("devrait avoir le role tooltip", () => {
    const wrapper = mount(NtTooltip, {
      props: { text: "Info" },
      slots: { default: "i" },
    });
    const tooltip = wrapper.find('[role="tooltip"]');
    expect(tooltip.exists()).toBe(true);
  });

  it("devrait appliquer la position top par defaut", () => {
    const wrapper = mount(NtTooltip, {
      props: { text: "Texte" },
      slots: { default: "?" },
    });
    const tooltip = wrapper.find('[role="tooltip"]');
    expect(tooltip.classes()).toContain("nt-tooltip--top");
  });

  it("devrait appliquer la position bottom", () => {
    const wrapper = mount(NtTooltip, {
      props: { text: "Texte", position: "bottom" },
      slots: { default: "?" },
    });
    const tooltip = wrapper.find('[role="tooltip"]');
    expect(tooltip.classes()).toContain("nt-tooltip--bottom");
  });
});
