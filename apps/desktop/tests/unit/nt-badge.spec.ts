// @vitest-environment happy-dom
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import NtBadge from "../../src/renderer/src/components/ui/NtBadge.vue";

describe("NtBadge", () => {
  it("devrait afficher le contenu par defaut", () => {
    const wrapper = mount(NtBadge, { slots: { default: "Test" } });
    expect(wrapper.text()).toBe("Test");
  });

  it("devrait appliquer la classe variant par defaut", () => {
    const wrapper = mount(NtBadge, { slots: { default: "Test" } });
    expect(wrapper.classes()).toContain("nt-badge--default");
  });

  it("devrait appliquer la classe variant success", () => {
    const wrapper = mount(NtBadge, {
      props: { variant: "success" },
      slots: { default: "OK" },
    });
    expect(wrapper.classes()).toContain("nt-badge--success");
  });

  it("devrait appliquer la classe size sm", () => {
    const wrapper = mount(NtBadge, {
      props: { size: "sm" },
      slots: { default: "Petit" },
    });
    expect(wrapper.classes()).toContain("nt-badge--sm");
  });

  it("devrait appliquer la classe size md par defaut", () => {
    const wrapper = mount(NtBadge, { slots: { default: "Moyen" } });
    expect(wrapper.classes()).toContain("nt-badge--md");
  });
});
