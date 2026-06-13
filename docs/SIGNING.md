# Code signing NovelTrad releases

Authenticode code signing is **not** required for NovelTrad v4 to
ship or to auto-update, but it is **strongly recommended** for any
distribution channel that touches end-user trust signals (SmartScreen,
Defender SmartScreen, etc.).

This document explains how to plug a signing certificate into the
existing build pipeline.

## Where signing happens

`NovelTrad.iss` defines a `SignTool` macro that activates only when
the `SIGNTOOL_PFX` environment variable is set:

```pascal
#define SignTool \
  (GetEnv("SIGNTOOL_PFX") != "" ? \
    "signtool sign /f $q%SIGNTOOL_PFX%$q /p %SIGNTOOL_PFX_PASSWORD% /tr http://timestamp.digicert.com /td sha256 /fd sha256 $f" : \
    "")
```

The `SignTool` and `SignedUninstaller=yes` directives in `[Setup]`
then run `signtool` on the generated installer and uninstaller
(`Setup_NovelTrad-vX.Y.Z.exe` and the embedded `unins000.exe`).
When `SIGNTOOL_PFX` is empty, `SignTool` is the empty string and
Inno Setup skips signing entirely — this is the "developer machine"
mode.

## Local signing (developer machine)

1. Acquire a code-signing certificate. For local testing you can
   create a self-signed one:
   ```powershell
   New-SelfSignedCertificate `
     -Subject "CN=NovelTrad Dev" `
     -Type CodeSigningCert `
     -CertStoreLocation "Cert:\CurrentUser\My"
   ```
   Export the certificate (with the private key) to a `.pfx` file
   you keep **out of source control**.

2. Set the env vars before building:
   ```powershell
   $env:SIGNTOOL_PFX = "C:\secrets\noveltrad-dev.pfx"
   $env:SIGNTOOL_PFX_PASSWORD = "…"
   python build.py --installer
   ```

3. Verify the signature:
   ```powershell
   signtool verify /pa Setup_NovelTrad-vX.Y.Z.exe
   ```

## CI signing (release workflow)

In `.github/workflows/release.yml`, add a step that imports the
certificate and exposes the env vars before `python build.py --all`:

```yaml
- name: Import code-signing cert
  if: env.SIGNTOOL_PFX_BASE64 != ''
  shell: pwsh
  run: |
      $bytes = [Convert]::FromBase64String("${{ secrets.SIGNTOOL_PFX_BASE64 }}")
      $path = Join-Path $env:TEMP "noveltrad.pfx"
      [IO.File]::WriteAllBytes($path, $bytes)
      "SIGNTOOL_PFX=$path" | Out-File -FilePath $env:GITHUB_ENV -Append
      "SIGNTOOL_PFX_PASSWORD=${{ secrets.SIGNTOOL_PFX_PASSWORD }}" | Out-File -FilePath $env:GITHUB_ENV -Append
```

- Store the base64-encoded `.pfx` in the repository's GitHub Actions
  secrets as `SIGNTOOL_PFX_BASE64`.
- Store the password as `SIGNTOOL_PFX_PASSWORD`.
- The step is a no-op (`if: env.SIGNTOOL_PFX_BASE64 != ''`) on
  repositories that don't have the secret, so the workflow keeps
  working unsigned.

## Auto-updater and signatures

The updater verifies **SHA256** of the downloaded installer against
the `sha256` field in `latest.json` (the manifest written by
`release.yml`). On Windows frozen builds it also runs a best-effort
`signtool verify /pa` check before launching the installer when
`signtool.exe` is available.

The Authenticode check is not a hard runtime dependency. Many user
machines do not have the Windows SDK installed, so the channel still
relies on HTTPS + SHA256 pinned in the release manifest as its
baseline integrity protection.

## EV certificates (out of scope for v4)

Extended Validation (EV) certs require a hardware token (USB
HID/smartcard) and cannot usually be used from a headless CI runner.
If you have an EV cert:

- Sign the installer manually after the CI runs.
- Re-attach the signed installer to the same GitHub release.
- The `latest.json` `sha256` must be recomputed against the signed
  artefact; otherwise auto-update will fail with a SHA256 mismatch.

## Costs and renewal

A standard OV code-signing certificate is roughly
`$70–$200/year` from a public CA (Sectigo, DigiCert). The cert
lifetime is typically 1–3 years; renew before expiry so the
timestamp authority keeps producing valid signatures.

SmartScreen reputation still requires a few thousand downloads
before the "Windows protected your PC" prompt goes away, even with
a valid signature. New releases are expected to trigger it briefly.
