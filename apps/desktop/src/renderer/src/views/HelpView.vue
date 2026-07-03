<script setup lang="ts">
import { BookOpen, Workflow, BookMarked, Download, Puzzle, Settings, Wand2 } from "@lucide/vue";

const sections = [
  {
    icon: BookOpen,
    title: "1. Créer un projet",
    content: "Depuis l'écran d'Accueil, cliquez sur « Nouveau projet ». Renseignez le nom, la langue source (ex: chinois) et la langue cible (ex: français). Le projet est un dossier autonome contenant tous les fichiers.",
  },
  {
    icon: Download,
    title: "2. Importer un chapitre",
    content: "Dans l'écran Chapitres, cliquez sur « Importer ». Glissez-déposez vos fichiers (TXT, DOCX, EPUB, Markdown). L'application détecte automatiquement l'encodage et découpe le texte en paragraphes.",
  },
  {
    icon: Workflow,
    title: "3. Traduire",
    content: "Sélectionnez un chapitre et cliquez sur « Traduire ». Le workflow multi-agent s'exécute : découpage → pré-traduction → traduction IA → cohérence → lexique → grammaire → style → polish → QA → export. Vous pouvez suivre la progression en temps réel.",
  },
  {
    icon: Wand2,
    title: "4. Vérifier et corriger",
    content: "Le score qualité (0-100) évalue 8 dimensions : cohérence, grammaire, fluidité, style, lexique, hallucinations, longueur, dialogues. Si le score est < 70, le workflow se met en pause. Vous pouvez relancer l'étape faible ou corriger manuellement dans l'éditeur côte à côte.",
  },
  {
    icon: BookMarked,
    title: "5. Gérer le lexique",
    content: "Le lexique garantit la cohérence des noms propres (personnages, lieux, techniques). Verrouillez les termes importants (icône 🔒). Les alias permettent de résoudre les variantes. L'extraction automatique propose des termes candidats.",
  },
  {
    icon: Download,
    title: "6. Exporter",
    content: "Une fois satisfait, exportez au format Markdown, TXT, DOCX, EPUB ou HTML. Le mode bilingue (source + traduction) est disponible pour EPUB et HTML. L'export par lots permet de traiter plusieurs chapitres à la fois.",
  },
  {
    icon: Puzzle,
    title: "7. Étendre avec des plugins",
    content: "NovelTrad supporte les plugins pour ajouter des agents, des formats d'export, des providers IA ou des workflows personnalisés. Déposez les plugins dans le dossier `plugins/` (accessible depuis Paramètres → Plugins).",
  },
  {
    icon: Settings,
    title: "8. Configurer",
    content: "Dans Paramètres, vous pouvez : changer de modèle IA (Ollama local recommandé), configurer un provider de fallback, ajuster les seuils de qualité, activer/désactiver des étapes du workflow, et choisir le canal de mise à jour (stable/beta).",
  },
];

const shortcuts = [
  { key: "Ctrl+N", action: "Nouveau projet" },
  { key: "Ctrl+O", action: "Ouvrir un projet" },
  { key: "Ctrl+Shift+T", action: "Traduire le chapitre actif" },
  { key: "Escape", action: "Fermer la fenêtre modale" },
];

const faq = [
  { q: "Ollama n'est pas détecté", a: "Vérifiez qu'Ollama est installé et lancé. L'application tente de se connecter sur http://localhost:11434. Vous pouvez changer l'adresse dans Paramètres → IA." },
  { q: "La traduction est lente", a: "Utilisez un modèle rapide pour la pré-traduction (qwen3.5:4b) et un modèle de qualité pour la traduction finale (qwen3.5:9b). Activez le cache IA dans Paramètres → Avancé." },
  { q: "Le score qualité est faible", a: "Enrichissez votre lexique avec les termes verrouillés. Vérifiez le rapport de cohérence pour identifier les paragraphes manquants ou les noms propres non traduits." },
  { q: "Comment installer un plugin ?", a: "Copiez le dossier du plugin dans le répertoire `plugins/` de NovelTrad. Le chemin exact est affiché dans Paramètres → Plugins. Redémarrez l'application." },
];
</script>

<template>
  <div class="help">
    <h1>Aide</h1>
    <p class="subtitle">Guide d'utilisation de NovelTrad 2.0</p>

    <!-- Guide étape par étape -->
    <section class="section">
      <h2>🚀 Démarrage rapide</h2>
      <div class="steps">
        <div v-for="s in sections" :key="s.title" class="step">
          <component :is="s.icon" class="step-icon" :size="22" />
          <div>
            <strong>{{ s.title }}</strong>
            <p>{{ s.content }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Raccourcis clavier -->
    <section class="section">
      <h2>⌨️ Raccourcis clavier</h2>
      <table class="shortcuts-table">
        <thead>
          <tr>
            <th>Raccourci</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in shortcuts" :key="s.key">
            <td><code>{{ s.key }}</code></td>
            <td>{{ s.action }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- FAQ -->
    <section class="section">
      <h2>❓ Questions fréquentes</h2>
      <div v-for="f in faq" :key="f.q" class="faq-item">
        <strong>Q : {{ f.q }}</strong>
        <p>R : {{ f.a }}</p>
      </div>
    </section>

    <!-- À propos -->
    <section class="section">
      <h2>📦 À propos</h2>
      <p>
        <strong>NovelTrad 2.0</strong> — Moteur de traduction de romans assisté par IA multi-agent.<br />
        Licence MIT. Développé par Balrog57.<br />
        <a href="https://github.com/Balrog57/noveltrad" target="_blank">GitHub</a>
      </p>
    </section>
  </div>
</template>

<style scoped>
.help {
  padding: 32px;
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  font-size: 28px;
  margin: 0 0 4px;
  color: var(--accent);
}

.subtitle {
  color: var(--text-secondary);
  margin: 0 0 32px;
  font-size: 14px;
}

.section {
  margin-bottom: 32px;
}

.section h2 {
  font-size: 18px;
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--bg-tertiary);
}

.steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
}

.step-icon {
  color: var(--accent);
  margin-top: 2px;
  flex-shrink: 0;
}

.step strong {
  display: block;
  margin-bottom: 4px;
}

.step p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.shortcuts-table {
  width: 100%;
  border-collapse: collapse;
}

.shortcuts-table th,
.shortcuts-table td {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid var(--bg-tertiary);
}

.shortcuts-table th {
  font-size: 12px;
  text-transform: uppercase;
  color: var(--text-secondary);
}

code {
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-family: "JetBrains Mono", monospace;
}

.faq-item {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
}

.faq-item strong {
  display: block;
  margin-bottom: 4px;
}

.faq-item p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

a {
  color: var(--accent);
}
</style>
