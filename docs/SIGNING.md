# Code Signing — Guide de configuration

Ce document explique comment configurer la signature de code pour les
releases Electron de NovelTrad (SDD §21.8). La signature authentifie
l'éditeur et empêche les avertissements SmartScreen (Windows) /
Gatekeeper (macOS).

## État actuel

- `electron-builder.yml` : `forceCodeSigning: false` (signature désactivée)
- Les variables d'environnement CI sont prêtes dans `.github/workflows/release.yml`
- **Bloqueur** : aucun certificat Authenticode (Windows) ni Apple Developer ID
  (macOS) n'est encore configuré

## Activation de la signature

Quand un certificat sera disponible :

1. Modifier `apps/desktop/electron-builder.yml` :
   ```yaml
   forceCodeSigning: true            # ← false → true
   ```
   Sous `win:` :
   ```yaml
   verifyUpdateCodeSignature: true   # ← false → true
   signAndEditExecutable: true       # ← false → true
   ```
   Sous `mac:` :
   ```yaml
   hardenRuntime: true
   notarize:
     teamId: your-team-id
   ```

2. Configurer les secrets CI (GitHub → repo → Settings → Secrets):
   - `CSC_LINK` : certificat Authenticode (.pfx/.p12) encodé en base64
   - `CSC_KEY_PASSWORD` : mot de passe du certificat
   - `APPLE_ID` : identifiant Apple Developer
   - `APPLE_APP_SPECIFIC_PASSWORD` : mot de passe spécifique application
   - `APPLE_TEAM_ID` : ID d'équipe Apple (10 caractères)

## Obtenir un certificat

### Windows — Authenticode

1. Acheter un certificat chez une autorité reconnue (DigiCert, Sectigo,
   Comodo…). Un certificat **EV Code Signing** est recommandé pour éviter
   SmartScreen.
2. Exporter le certificat au format `.pfx` ou `.p12` avec sa clé privée.
3. Encoder en base64 :
   ```bash
   base64 -w0 cert.pfx > cert-base64.txt
   ```
4. Copier le contenu dans le secret GitHub `CSC_LINK`.

### macOS — Apple Developer ID

1. Créer un compte [Apple Developer](https://developer.apple.com)
   ($99/an).
2. Générer un certificat **Developer ID Application** via Xcode ou
   le portail Apple Developer.
3. Générer un **App-Specific Password** sur
   [appleid.apple.com](https://appleid.apple.com).
4. Configurer les secrets GitHub : `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`,
   `APPLE_TEAM_ID`.

## Vérifier la signature

### Windows
```powershell
Get-AuthenticodeSignature NovelTrad-2.x.x-setup.exe
```

### macOS
```bash
codesign --verify --deep --strict NovelTrad.app
spctl --assess --verbose NovelTrad.app
```

## Signature locale (test)

Pour tester la signature en local avant CI :

```bash
# Windows (PowerShell)
$env:CSC_LINK = "cert.pfx"
$env:CSC_KEY_PASSWORD = "your-password"
npx electron-builder --win --publish never

# macOS
export APPLE_ID="your-id@example.com"
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export APPLE_TEAM_ID="ABCDEF1234"
npx electron-builder --mac --publish never
```

## Références

- [electron-builder — Code Signing](https://www.electron.build/code-signing)
- [electron-builder — Windows](https://www.electron.build/win#code-signing)
- [electron-builder — macOS](https://www.electron.build/mac)
- [SDD §21.8 — Signature de code](../../docs/audit/GAP_ANALYSIS_2.1.3_to_SDD.md)
