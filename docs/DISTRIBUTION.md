# Drops — Guida alla Distribuzione

## 📦 Come Preparare e Condividere il DMG

## Regola principale: niente autorizzazione automatica

Un’app non può approvare sé stessa durante l’installazione: Gatekeeper la
controlla prima che il suo codice possa partire. Script che disattivano
Gatekeeper o rimuovono automaticamente la quarantena peggiorano sicurezza e UX.

Distribuzione corretta:

1. firma `Developer ID Application`;
2. notarizzazione Apple;
3. ticket notarizzazione applicato al DMG;
4. verifica Gatekeeper prima della pubblicazione.

`build-dmg.sh` automatizza questi passaggi quando trova configurazione Apple.

### Configurazione una tantum

Serve account Apple Developer con certificato `Developer ID Application`
installato nel Portachiavi.

Mostra identità disponibili:

```bash
security find-identity -v -p codesigning
```

Salva credenziali notarizzazione nel Portachiavi. Usa password specifica per app,
non password principale Apple:

```bash
xcrun notarytool store-credentials "drops-notary" \
  --apple-id "EMAIL_APPLE_ID" \
  --team-id "TEAM_ID"
```

`notarytool` chiederà password specifica per app e la conserverà nel
Portachiavi.

Prima della build:

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: NOME (TEAM_ID)"
export DROPS_NOTARY_PROFILE="drops-notary"
./build-dmg.sh
```

Non salvare password, certificati o segreti nel repository.

Senza queste variabili, script produce build locale non notarizzata e avvisa
chiaramente che Gatekeeper può bloccarla.

### Step 1: Build del Progetto

```bash
cd /Users/gianco/Documents/Claude/Projects/mp3-downloader

# Rebuilda il Tauri app (se hai fatto modifiche)
cd src-tauri
cargo tauri build --target universal2

# Aspetta che finisca (5-10 minuti circa)
```

**Output**: Il DMG sarà in:
```
src-tauri/target/release/bundle/dmg/Drops.dmg
```

### Step 2: Verifica che Funzioni

Prima di mandarlo all'amico, testalo su una macchina diversa (o simula il setup):

```bash
# Copia il DMG da un'altra parte per testare
cp src-tauri/target/release/bundle/dmg/Drops.dmg ~/Desktop/Drops-test.dmg

# Apri il DMG dal Desktop e installa
open ~/Desktop/Drops-test.dmg
```

**Checklist di verifica:**
- ✅ `codesign --verify --deep --strict Drops.app` riesce
- ✅ `xcrun stapler validate Drops.dmg` riesce
- ✅ `spctl --assess` accetta il DMG
- ✅ L'app parte senza errori
- ✅ Riesci a scaricare un video
- ✅ Il file viene salvato
- ✅ I log appaiono in `~/.drops/logs/backend.log`

### Step 3: Condividi l'Amico

Hai 3 opzioni:

#### **Opzione A: Via Email/Cloud (Consigliato)**
1. Carica il DMG su Google Drive / Dropbox / iCloud
2. Manda al tuo amico il link pubblico
3. L'amico scarica e installa

```bash
# Dimensione del DMG
du -h src-tauri/target/release/bundle/dmg/Drops.dmg
# ~50-80 MB circa
```

#### **Opzione B: AirDrop (Solo macOS)
Se sei fisicamente vicino:
```bash
# Copia il DMG nel Finder
# Usa AirDrop per mandarlo
```

#### **Opzione C: USB Stick
Se internet è lento/poco affidabile:
```bash
# Copia il DMG su una USB formattata
cp src-tauri/target/release/bundle/dmg/Drops.dmg /Volumes/USBName/Drops.dmg
```

---

### Step 4: Comunica all'Amico

Manda questo messaggio:

> **Drops v0.1 — Setup**
> 
> Ciao! Ti mando Drops, un'app per scaricare video da YouTube.
>
> **Setup (2 minuti):**
> 1. Apri il DMG allegato
> 2. Trascina Drops.app nella cartella Applications
> 3. Lancia l'app da Applications
> 4. Accetta solo i permessi macOS necessari a cartelle e unità che vuoi usare.
> 5. Fatto! Nessuna password da ricordare.
>
> Se hai problemi, i log sono in: `~/.drops/logs/backend.log`
>
> Link: [DMG Link]
> Guida completa: Vedi SETUP.md

---

## 🔄 Aggiornamenti Futuri

Al momento gli aggiornamenti sono **manuali** (Fase 2 pianifica auto-update). Quando hai nuove versioni:

1. Rebuilda il DMG
2. Manda il link al nuovo DMG all'amico
3. L'amico ripete lo Step 1 di SETUP.md

In futuro questo sarà automatico.

---

## ⚠️ Cosa Cambia con Questi Fix

| Aspetto | Prima | Dopo |
|---------|--------|-------|
| **Portabilità** | 🔴 Bloccata da path hardcoded | ✅ Funziona su qualsiasi Mac |
| **Autenticazione** | 🔴 Password unica (hardcoded) | ✅ Token univoco per utente |
| **Debug** | 🔴 Niente log | ✅ Log persistente in ~/.drops/logs/ |
| **Setup Utente** | 🔴 Manuale + complicato | ✅ Zero friction, automatico |

---

## 📋 Checklist Pre-Distribuzione

Usa questa checklist prima di mandare il DMG a chiunque:

- [ ] Tutti i 3 fix (path, auth, logging) sono committati
- [ ] Ho rebuildato il DMG con `cargo tauri build`
- [ ] App firmata con `Developer ID Application`
- [ ] DMG notarizzato e ticket applicato
- [ ] `spctl --assess` accetta il DMG
- [ ] Ho testato il DMG su un'altra macchina (o almeno rinominato e reinstallato)
- [ ] I log vengono creati correttamente in ~/.drops/logs/
- [ ] Il token viene generato in ~/.drops/config.json
- [ ] Ho condiviso SETUP.md con l'amico
- [ ] L'amico sa dove trovare i log se ha problemi

---

## 🚀 Prossimo Step: Fase 2 (Distribuzione)

Quando sei pronto per distribuire a più utenti:

- [ ] **D1**: Migliorare l'installer (DMG personalizzato con icone/sfondo)
- [ ] **D2**: Auto-update (in-app check + download automatico)
- [ ] **D3**: Per-user auth (UI per gestire token, revocare accessi)
- [ ] **D4**: Docs migliori (video setup, FAQ)
- [ ] **D5**: Monitoring produzione (errori centrali su Sentry)

Per adesso, questi 3 fix ti permettono di mandare l'app a chiunque senza rischi.

---
