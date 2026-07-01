// @vitest-environment happy-dom
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import NtButton from "../../src/renderer/src/components/ui/NtButton.vue";
import NtInput from "../../src/renderer/src/components/ui/NtInput.vue";
import NtSelect, {
  type SelectOption,
} from "../../src/renderer/src/components/ui/NtSelect.vue";
import NtTextarea from "../../src/renderer/src/components/ui/NtTextarea.vue";
import NtCard from "../../src/renderer/src/components/ui/NtCard.vue";
import NtLogViewer, {
  type LogEntry,
} from "../../src/renderer/src/components/ui/NtLogViewer.vue";

// ---------------------------------------------------------------------------
// NtButton
// ---------------------------------------------------------------------------

describe("NtButton", () => {
  it("devrait afficher le contenu du slot", () => {
    const wrapper = mount(NtButton, { slots: { default: "Valider" } });
    expect(wrapper.text()).toBe("Valider");
  });

  it("devrait appliquer la variante primary par defaut", () => {
    const wrapper = mount(NtButton, { slots: { default: "OK" } });
    expect(wrapper.classes()).toContain("nt-button--primary");
  });

  it("devrait appliquer la variante danger", () => {
    const wrapper = mount(NtButton, {
      props: { variant: "danger" },
      slots: { default: "Supprimer" },
    });
    expect(wrapper.classes()).toContain("nt-button--danger");
  });

  it("devrait emettre click au clic", async () => {
    const wrapper = mount(NtButton, { slots: { default: "OK" } });
    await wrapper.trigger("click");
    expect(wrapper.emitted("click")).toHaveLength(1);
  });

  it("ne devrait pas emettre click quand disabled", async () => {
    const wrapper = mount(NtButton, {
      props: { disabled: true },
      slots: { default: "OK" },
    });
    await wrapper.trigger("click");
    expect(wrapper.emitted("click")).toBeUndefined();
  });

  it("ne devrait pas emettre click quand loading", async () => {
    const wrapper = mount(NtButton, {
      props: { loading: true },
      slots: { default: "OK" },
    });
    await wrapper.trigger("click");
    expect(wrapper.emitted("click")).toBeUndefined();
  });

  it("devrait afficher un spinner quand loading", () => {
    const wrapper = mount(NtButton, {
      props: { loading: true },
      slots: { default: "Chargement" },
    });
    expect(wrapper.find(".nt-button-spinner").exists()).toBe(true);
  });

  it("devrait appliquer la taille lg", () => {
    const wrapper = mount(NtButton, {
      props: { size: "lg" },
      slots: { default: "Grand" },
    });
    expect(wrapper.classes()).toContain("nt-button--lg");
  });
});

// ---------------------------------------------------------------------------
// NtInput
// ---------------------------------------------------------------------------

describe("NtInput", () => {
  it("devrait afficher le label", () => {
    const wrapper = mount(NtInput, { props: { label: "Nom du projet" } });
    expect(wrapper.text()).toContain("Nom du projet");
  });

  it("devrait afficher l'erreur", () => {
    const wrapper = mount(NtInput, {
      props: { label: "Titre", error: "Le titre est requis" },
    });
    expect(wrapper.text()).toContain("Le titre est requis");
    expect(wrapper.find('[role="alert"]').exists()).toBe(true);
  });

  it("devrait emettre update:modelValue a la saisie", async () => {
    const wrapper = mount(NtInput, { props: { modelValue: "" } });
    const input = wrapper.find("input");
    await input.setValue("Nouveau texte");
    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")![0]).toEqual(["Nouveau texte"]);
  });

  it("devrait afficher l'icone quand fournie", () => {
    const wrapper = mount(NtInput, {
      props: { icon: "🔍", modelValue: "" },
    });
    expect(wrapper.find(".nt-input-icon").exists()).toBe(true);
    expect(wrapper.text()).toContain("🔍");
  });

  it("devrait desactiver l'input quand disabled", () => {
    const wrapper = mount(NtInput, {
      props: { disabled: true, modelValue: "" },
    });
    expect(wrapper.find("input").attributes("disabled")).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// NtSelect
// ---------------------------------------------------------------------------

describe("NtSelect", () => {
  const options: SelectOption[] = [
    { value: "fr", label: "Français" },
    { value: "en", label: "Anglais" },
  ];

  it("devrait afficher le label", () => {
    const wrapper = mount(NtSelect, {
      props: { label: "Langue cible", options },
    });
    expect(wrapper.text()).toContain("Langue cible");
  });

  it("devrait afficher toutes les options", () => {
    const wrapper = mount(NtSelect, { props: { options } });
    const optionEls = wrapper.findAll("option");
    expect(optionEls).toHaveLength(2);
    expect(optionEls[0].text()).toBe("Français");
    expect(optionEls[1].text()).toBe("Anglais");
  });

  it("devrait emettre update:modelValue au changement", async () => {
    const wrapper = mount(NtSelect, {
      props: { modelValue: "fr", options },
    });
    const select = wrapper.find("select");
    await select.setValue("en");
    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")![0]).toEqual(["en"]);
  });

  it("devrait desactiver le select quand disabled", () => {
    const wrapper = mount(NtSelect, {
      props: { disabled: true, options },
    });
    expect(wrapper.find("select").attributes("disabled")).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// NtTextarea
// ---------------------------------------------------------------------------

describe("NtTextarea", () => {
  it("devrait afficher le label", () => {
    const wrapper = mount(NtTextarea, { props: { label: "Description" } });
    expect(wrapper.text()).toContain("Description");
  });

  it("devrait emettre update:modelValue a la saisie", async () => {
    const wrapper = mount(NtTextarea, { props: { modelValue: "" } });
    const textarea = wrapper.find("textarea");
    await textarea.setValue("Texte long");
    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")![0]).toEqual(["Texte long"]);
  });

  it("devrait afficher l'erreur", () => {
    const wrapper = mount(NtTextarea, {
      props: { label: "Notes", error: "Champ obligatoire" },
    });
    expect(wrapper.text()).toContain("Champ obligatoire");
    expect(wrapper.find('[role="alert"]').exists()).toBe(true);
  });

  it("devrait avoir l'attribut rows par defaut a 4", () => {
    const wrapper = mount(NtTextarea, { props: { modelValue: "" } });
    expect(wrapper.find("textarea").attributes("rows")).toBe("4");
  });

  it("devrait desactiver le textarea quand disabled", () => {
    const wrapper = mount(NtTextarea, {
      props: { disabled: true, modelValue: "" },
    });
    expect(wrapper.find("textarea").attributes("disabled")).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// NtCard
// ---------------------------------------------------------------------------

describe("NtCard", () => {
  it("devrait afficher le titre dans l'en-tete", () => {
    const wrapper = mount(NtCard, {
      props: { title: "Statistiques" },
      slots: { default: "Contenu" },
    });
    expect(wrapper.find(".nt-card-title").text()).toBe("Statistiques");
  });

  it("devrait afficher le contenu du slot par defaut", () => {
    const wrapper = mount(NtCard, {
      props: { title: "Carte" },
      slots: { default: "Corps de la carte" },
    });
    expect(wrapper.find(".nt-card-body").text()).toBe("Corps de la carte");
  });

  it("devrait afficher les actions dans le slot actions", () => {
    const wrapper = mount(NtCard, {
      props: { title: "Projet" },
      slots: {
        actions: '<button class="test-action">Modifier</button>',
      },
    });
    expect(wrapper.find(".nt-card-actions").exists()).toBe(true);
    expect(wrapper.find(".test-action").exists()).toBe(true);
  });

  it("ne devrait pas afficher d'en-tete sans titre ni slots header/actions", () => {
    const wrapper = mount(NtCard, { slots: { default: "Contenu" } });
    expect(wrapper.find(".nt-card-header").exists()).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// NtLogViewer
// ---------------------------------------------------------------------------

describe("NtLogViewer", () => {
  const entries: LogEntry[] = [
    {
      level: "info",
      message: "Démarrage de l'application",
      timestamp: "10:00",
    },
    { level: "warn", message: "Ressource faible", timestamp: "10:01" },
    { level: "error", message: "Échec de connexion", timestamp: "10:02" },
    { level: "debug", message: "Variable x=42", timestamp: "10:03" },
  ];

  it("devrait afficher tous les messages de log", () => {
    const wrapper = mount(NtLogViewer, { props: { entries } });
    expect(wrapper.text()).toContain("Démarrage de l'application");
    expect(wrapper.text()).toContain("Ressource faible");
    expect(wrapper.text()).toContain("Échec de connexion");
    expect(wrapper.text()).toContain("Variable x=42");
  });

  it("devrait appliquer la classe de niveau a chaque entree", () => {
    const wrapper = mount(NtLogViewer, { props: { entries } });
    expect(wrapper.find(".nt-log-entry--info").exists()).toBe(true);
    expect(wrapper.find(".nt-log-entry--warn").exists()).toBe(true);
    expect(wrapper.find(".nt-log-entry--error").exists()).toBe(true);
    expect(wrapper.find(".nt-log-entry--debug").exists()).toBe(true);
  });

  it("devrait afficher un message vide quand aucune entree", () => {
    const wrapper = mount(NtLogViewer, { props: { entries: [] } });
    expect(wrapper.find(".nt-log-empty").exists()).toBe(true);
    expect(wrapper.text()).toContain("Aucun log à afficher.");
  });

  it("devrait avoir le role log", () => {
    const wrapper = mount(NtLogViewer, { props: { entries: [] } });
    expect(wrapper.find('[role="log"]').exists()).toBe(true);
  });

  it("devrait afficher les horodatages quand fournis", () => {
    const wrapper = mount(NtLogViewer, { props: { entries } });
    const times = wrapper.findAll(".nt-log-time");
    expect(times).toHaveLength(4);
    expect(times[0].text()).toBe("10:00");
  });
});
