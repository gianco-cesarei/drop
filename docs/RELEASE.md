# Pubblicare una Release di Drops

macOS è piattaforma supportata. Windows resta sperimentale e viene compilato
solo avviando manualmente workflow GitHub Actions.

## Gate obbligatori

Prima di creare tag:

1. versione sincronizzata in `package.json`, `package-lock.json`,
   `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`, lockfile e backend;
2. build DMG completata;
3. test installazione da DMG;
4. download YouTube e SoundCloud;
5. cartella scelta, coda e clip video;
6. controllo aggiornamenti;
7. firma e notarizzazione per Release pubblica.

Build `1.0.5` è privata. Diventa `1.1.0` solo dopo superamento gate.

## Ordine Release

Tag deve puntare al commit con modifiche:

```text
modifica → test → bump stabile → commit → push commit → tag → push tag
```

Mai taggare commit vecchio.

```bash
git add -A
git commit -m "Release vX.Y.Z"
git push origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

Push tag avvia job macOS e pubblica:

- `Drops-vX.Y.Z-macOS.dmg`;
- `LEGGIMI-Installazione-Drops-Mac.txt`.

Artifact Actions è interno. Utenti scaricano DMG dalla Release.

## Windows

Job Windows:

- parte solo con `workflow_dispatch`;
- produce artifact interno;
- non allega EXE alla Release pubblica;
- non implica supporto ufficiale.

Pubblicazione Windows richiede test reali Windows 10 e 11.

## macOS

Release pubblica deve usare `Developer ID Application`, notarizzazione Apple e
ticket applicato. `build-dmg.sh` usa:

- `APPLE_SIGNING_IDENTITY`;
- `DROPS_NOTARY_PROFILE`.

Build privata non notarizzata può richiedere:

`Impostazioni di Sistema → Privacy e sicurezza → Apri comunque`

Non disattivare Gatekeeper. Non rimuovere automaticamente quarantena.

Vedi:

- `docs/DISTRIBUTION.md`;
- `docs/INSTALLAZIONE_MACOS.md`.
