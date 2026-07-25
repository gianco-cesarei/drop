# Pubblicare una release di Drops (Windows)

Riferimento rapido. La logica completa è nell'agente `.claude/agents/drops-release.md`
(chiedi in chat "pubblica la release vX.Y.Z" e parte lui).

## Regola d'oro
Il tag deve puntare al commit con le modifiche. Ordine tassativo:
**modifica → commit → push del commit → poi crea il tag → push del tag.**
Mai taggare un commit vecchio: la Release non verrebbe creata.

## Passi

1. Porta la versione a `X.Y.Z` (stessa del tag `vX.Y.Z`) in:
   `src-tauri/tauri.conf.json`, `package.json`, `src-tauri/Cargo.toml`.
   Aggiorna `CHANGELOG.md`.

2. Commit + push:
   ```bash
   cd ~/Documents/Claude/Projects/mp3-downloader
   find .git -name '*.lock' -delete
   git add -A
   git commit -m "Release vX.Y.Z"
   git log --oneline -1        # deve mostrare l'hash NUOVO
   git push
   ```

3. Tag sul commit nuovo + push (scatena build e Release):
   ```bash
   git push origin :refs/tags/vX.Y.Z 2>/dev/null; git tag -d vX.Y.Z 2>/dev/null
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. Su **Actions** verifica che il run mostri il commit giusto e diventi verde.

5. Su **Releases** compare `Drops vX.Y.Z` con `Drops_X.Y.Z_x64-setup.exe`.
   Il link è pubblico: condivisibile con chiunque, senza account GitHub.

## Se la Release non compare
Run verde ma niente Release → apri lo step "Publish GitHub Release" nei log.
Di solito: tag su commit sbagliato (rifai 2-3) o permessi token
(`permissions: contents: write` nel workflow + Settings → Actions → General
con permessi di scrittura ai workflow).

## Note
- Artifact di Actions = solo per te (loggato). Per gli utenti esterni serve la Release.
- App non firmata → SmartScreen al primo avvio ("Ulteriori informazioni" → "Esegui comunque").
