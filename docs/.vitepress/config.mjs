import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'NovelTrad 2.0',
  description: 'Software Design Document pour NovelTrad 2.0',
  lang: 'fr-FR',
  base: '/noveltrad/',
  lastUpdated: true,

  themeConfig: {
    search: {
      provider: 'local'
    },

    nav: [
      { text: 'Accueil', link: '/' },
      {
        text: 'Volumes',
        items: [
          { text: 'Fondation', items: [
            { text: '00 — Vision', link: '/volumes/00-Vision' },
            { text: '01 — Architecture', link: '/volumes/01-Architecture' },
            { text: '02 — Installation', link: '/volumes/02-Installation' },
            { text: '03 — Gestion des modèles IA', link: '/volumes/03-AI-Models' }
          ]},
          { text: 'Application', items: [
            { text: '04 — Interface', link: '/volumes/04-UI-UX' },
            { text: '05 — Gestion des projets', link: '/volumes/05-Project-Management' },
            { text: '06 — Base de données', link: '/volumes/06-Database' }
          ]},
          { text: 'Moteur de traduction', items: [
            { text: '07 — Workflow', link: '/volumes/07-Workflow' },
            { text: '08 — Agents', link: '/volumes/08-Agents' },
            { text: '09 — Translation Memory', link: '/volumes/09-Translation-Memory' },
            { text: '10 — Lexique', link: '/volumes/10-Lexicon' },
            { text: '11 — Cohérence', link: '/volumes/11-Consistency' },
            { text: '12 — Qualité', link: '/volumes/12-Quality' },
            { text: '13 — Export', link: '/volumes/13-Export' }
          ]},
          { text: 'Fonctionnalités avancées', items: [
            { text: '14 — Historique', link: '/volumes/14-History' },
            { text: '15 — Plugins', link: '/volumes/15-Plugins' },
            { text: '16 — API interne', link: '/volumes/16-Internal-API' }
          ]},
          { text: 'Infrastructure', items: [
            { text: '17 — Auto Update', link: '/volumes/17-Auto-Update' },
            { text: '18 — Journalisation', link: '/volumes/18-Logging' },
            { text: '19 — Tests', link: '/volumes/19-Tests' },
            { text: '20 — CI/CD', link: '/volumes/20-CICD' },
            { text: '21 — Sécurité', link: '/volumes/21-Security' },
            { text: '22 — Performances', link: '/volumes/22-Performance' }
          ]},
          { text: 'Design & planification', items: [
            { text: '23 — Système de design', link: '/volumes/23-Design-System' },
            { text: '24 — Plan de développement', link: '/volumes/24-Development-Plan' },
            { text: '25 — Prompt Book', link: '/volumes/25-Prompt-Book' }
          ]}
        ]
      },
      {
        text: 'Ressources',
        items: [
          { text: "Cas d'usage", link: '/use-cases' },
          { text: "Inspirations & comparatif", link: '/inspirations' },
          { text: "Guide développeur", link: '/developer-guide' },
          { text: 'llms.txt', link: '/llms-txt' }
        ]
      }
    ],

    outline: {
      level: [2, 3],
      label: 'Sur cette page'
    },

    sidebar: [
      {
        text: 'Fondation',
        collapsed: false,
        items: [
          { text: '00 — Vision', link: '/volumes/00-Vision' },
          { text: '01 — Architecture', link: '/volumes/01-Architecture' },
          { text: '02 — Installation', link: '/volumes/02-Installation' },
          { text: '03 — Gestion des modèles IA', link: '/volumes/03-AI-Models' }
        ]
      },
      {
        text: 'Application',
        collapsed: false,
        items: [
          { text: '04 — Interface', link: '/volumes/04-UI-UX' },
          { text: '05 — Gestion des projets', link: '/volumes/05-Project-Management' },
          { text: '06 — Base de données', link: '/volumes/06-Database' }
        ]
      },
      {
        text: 'Moteur de traduction',
        collapsed: false,
        items: [
          { text: '07 — Workflow', link: '/volumes/07-Workflow' },
          { text: '08 — Agents', link: '/volumes/08-Agents' },
          { text: '09 — Translation Memory', link: '/volumes/09-Translation-Memory' },
          { text: '10 — Lexique', link: '/volumes/10-Lexicon' },
          { text: '11 — Cohérence', link: '/volumes/11-Consistency' },
          { text: '12 — Qualité', link: '/volumes/12-Quality' },
          { text: '13 — Export', link: '/volumes/13-Export' }
        ]
      },
      {
        text: 'Fonctionnalités avancées',
        collapsed: false,
        items: [
          { text: '14 — Historique', link: '/volumes/14-History' },
          { text: '15 — Plugins', link: '/volumes/15-Plugins' },
          { text: '16 — API interne', link: '/volumes/16-Internal-API' }
        ]
      },
      {
        text: 'Infrastructure',
        collapsed: false,
        items: [
          { text: '17 — Auto Update', link: '/volumes/17-Auto-Update' },
          { text: '18 — Journalisation', link: '/volumes/18-Logging' },
          { text: '19 — Tests', link: '/volumes/19-Tests' },
          { text: '20 — CI/CD', link: '/volumes/20-CICD' },
          { text: '21 — Sécurité', link: '/volumes/21-Security' },
          { text: '22 — Performances', link: '/volumes/22-Performance' }
        ]
      },
      {
        text: 'Design & planification',
        collapsed: false,
        items: [
          { text: '23 — Système de design', link: '/volumes/23-Design-System' },
          { text: '24 — Plan de développement', link: '/volumes/24-Development-Plan' },
          { text: '25 — Prompt Book', link: '/volumes/25-Prompt-Book' }
        ]
      },
      {
        text: 'Ressources',
        collapsed: false,
        items: [
          { text: 'Inspirations & comparatif', link: '/inspirations' },
          { text: 'Guide développeur', link: '/developer-guide' },
          { text: 'Cas d\'usage', link: '/use-cases' },
          { text: 'llms.txt', link: '/llms-txt' }
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Balrog57/noveltrad' }
    ],

    footer: {
      message: 'Produit sous licence MIT.',
      copyright: 'Copyright © 2026 NovelTrad'
    },

    docFooter: {
      prev: 'Précédent',
      next: 'Suivant'
    }
  },

  markdown: {
    config: (md) => {
      // Mermaid support via plugin if installed
    }
  },

  vite: {
    build: {
      assetsInlineLimit: 0
    }
  }
})
