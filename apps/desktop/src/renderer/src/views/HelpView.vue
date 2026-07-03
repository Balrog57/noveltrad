<script setup lang="ts">
</script>

<template>
  <div class="help">
    <h1 class="title">Aide - NovelTrad 2.0</h1>

    <section class="card">
      <h2>Demarrage rapide</h2>
      <ol>
        <li><strong>Creer un projet</strong> : Depuis l'ecran d'Accueil, cliquez sur « Nouveau projet ». Choix de la langue source et cible.</li>
        <li><strong>Importer un chapitre</strong> : Dans Chapitres, cliquez « Importer ». Formats acceptes : TXT, DOCX, EPUB, Markdown.</li>
        <li><strong>Traduire</strong> : Selectionnez un chapitre, cliquez « Traduire ». Le workflow multi-agent s'execute en 10 etapes.</li>
        <li><strong>Verifier</strong> : Le score qualite (0-100) evalue 8 dimensions. Score &lt; 70 = pause, vous pouvez corriger.</li>
        <li><strong>Exporter</strong> : Formats disponibles : Markdown, TXT, DOCX, EPUB, HTML. Mode bilingue possible.</li>
      </ol>
    </section>

    <section class="card">
      <h2>Raccourcis clavier</h2>
      <table>
        <tr><td><code>Ctrl+N</code></td><td>Nouveau projet</td></tr>
        <tr><td><code>Ctrl+O</code></td><td>Ouvrir un projet</td></tr>
        <tr><td><code>Ctrl+Shift+T</code></td><td>Traduire le chapitre actif</td></tr>
        <tr><td><code>Escape</code></td><td>Fermer la fenetre modale</td></tr>
      </table>
    </section>

    <section class="card">
      <h2>FAQ</h2>
      <div class="faq">
        <p><strong>Ollama non detecte ?</strong> Verifiez qu'Ollama est installe et lance. L'application se connecte sur http://localhost:11434.</p>
        <p><strong>Traduction lente ?</strong> Modele rapide recommande : qwen3.5:4b. Modele qualite : qwen3.5:9b.</p>
        <p><strong>Score faible ?</strong> Enrichissez le lexique, verrouillez les termes importants (icone cadenas).</p>
        <p><strong>Installer un plugin ?</strong> Copiez le dossier du plugin dans le repertoire plugins/ de NovelTrad.</p>
      </div>
    </section>

    <section class="card">
      <p class="about">NovelTrad 2.0 — Moteur de traduction de romans assiste par IA multi-agent. Licence MIT.</p>
    </section>
  </div>
</template>

<style scoped>
.help {
  padding: 32px;
  max-width: 800px;
  margin: 0 auto;
}

.title {
  font-size: 24px;
  color: var(--accent);
  margin: 0 0 24px;
}

.card {
  background: var(--bg-secondary);
  border-radius: var(--border-radius);
  padding: 20px;
  margin-bottom: 16px;
}

.card h2 {
  font-size: 16px;
  margin: 0 0 12px;
}

ol {
  margin: 0;
  padding-left: 20px;
}

li {
  margin-bottom: 6px;
  line-height: 1.5;
}

table {
  width: 100%;
  border-collapse: collapse;
}

td {
  padding: 6px 12px;
  border-bottom: 1px solid var(--bg-tertiary);
}

code {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 3px;
}

.faq p {
  margin: 0 0 10px;
  line-height: 1.5;
}

.about {
  color: var(--text-secondary);
  font-size: 13px;
  margin: 0;
}
</style>
