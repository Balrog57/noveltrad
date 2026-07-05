import { describe, it, expect, vi } from "vitest";

// Mock electron-log
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    transports: { file: { level: false }, console: { level: false } },
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

import AdmZip from "adm-zip";
import { ProjectManager } from "../../src/main/managers/ProjectManager";

/**
 * T10 — EPUB import with spine order (SDD §13.4)
 *
 * 4 tests :
 * 1. EPUB avec spine → chapitres dans l'ordre spine
 * 2. EPUB sans spine → fallback ordre alphabétique
 * 3. EPUB avec content.opf absent → erreur gérée
 * 4. EPUB multi-fichiers HTML → chaque fichier = un chapitre
 */

function createManagerForTesting(): ProjectManager {
  const mockSettings = {
    get: () => undefined,
    set: () => {},
  } as never;
  return new ProjectManager(mockSettings);
}

describe("ProjectManager — import EPUB (spine order)", () => {
  it("1. readEpubSpine: retourne les hrefs dans l'ordre du spine", () => {
    const zip = new AdmZip();

    // OPF avec spine et manifest
    const opf = `<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <manifest>
    <item id="chap3" href="chapter3.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chap2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="style.css" media-type="text/css"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
    <itemref idref="chap2"/>
    <itemref idref="chap3"/>
  </spine>
</package>`;
    zip.addFile("OEBPS/content.opf", Buffer.from(opf));

    const manager = createManagerForTesting();
    // readEpubSpine est une méthode publique accessible via as any
    const hrefs = (manager as unknown as Record<string, (z: AdmZip) => string[]>).readEpubSpine(zip);
    // The spine order should be chapter1, chapter2, chapter3
    expect(hrefs).toEqual(["chapter1.xhtml", "chapter2.xhtml", "chapter3.xhtml"]);
  });

  it("2. readEpubSpine: sans spine → retourne tableau vide (fallback)", () => {
    const zip = new AdmZip();

    const opf = `<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <manifest>
    <item id="chap1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
  </spine>
</package>`;
    zip.addFile("OEBPS/content.opf", Buffer.from(opf));

    const manager = createManagerForTesting();
    const hrefs = (manager as unknown as Record<string, (z: AdmZip) => string[]>).readEpubSpine(zip);
    expect(hrefs).toEqual([]);
  });

  it("3. readEpubSpine: content.opf absent → retourne tableau vide", () => {
    const zip = new AdmZip();
    zip.addFile("OEBPS/chapter1.xhtml", Buffer.from("<html><body>Chapter 1</body></html>"));

    const manager = createManagerForTesting();
    const hrefs = (manager as unknown as Record<string, (z: AdmZip) => string[]>).readEpubSpine(zip);
    expect(hrefs).toEqual([]);
  });

  it("4. readEpubSpine: multi-fichiers HTML avec spine → ordre préservé", () => {
    const zip = new AdmZip();

    // 3 fichiers HTML + 1 CSS
    zip.addFile("OEBPS/chapter3.xhtml", Buffer.from("<html><body>Trois</body></html>"));
    zip.addFile("OEBPS/chapter1.xhtml", Buffer.from("<html><body>Un</body></html>"));
    zip.addFile("OEBPS/chapter2.xhtml", Buffer.from("<html><body>Deux</body></html>"));
    zip.addFile("OEBPS/style.css", Buffer.from("body { color: black; }"));

    const opf = `<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <manifest>
    <item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="c2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
    <item id="c3" href="chapter3.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="style.css" media-type="text/css"/>
  </manifest>
  <spine>
    <itemref idref="c1"/>
    <itemref idref="c2"/>
    <itemref idref="c3"/>
  </spine>
</package>`;
    zip.addFile("OEBPS/content.opf", Buffer.from(opf));

    const manager = createManagerForTesting();
    const hrefs = (manager as unknown as Record<string, (z: AdmZip) => string[]>).readEpubSpine(zip);
    expect(hrefs).toEqual(["chapter1.xhtml", "chapter2.xhtml", "chapter3.xhtml"]);
  });
});
