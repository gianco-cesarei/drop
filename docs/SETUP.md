# Drops — Setup Guide

## 🚀 Prima volta: Setup Iniziale

### Per macOS (DMG Installer)

1. **Scarica il DMG** da [link qui]
2. **Apri il DMG** e trascina `Drops.app` nella cartella `Applications`
3. **Lancia l'app** dalla cartella Applications (la prima volta ti chiederà il permesso di Apple)
4. **Fatto!** L'app creerà automaticamente:
   - `~/.drops/config.json` — contiene il tuo token univoco
   - `~/.drops/logs/` — cartella dove l'app salva i log di debug

### Nessuna password da ricordare ✅
Il token viene generato automaticamente la prima volta. Se lo vuoi vedere:

```bash
cat ~/.drops/config.json
```

---

## ⚙️ Configurazione Avanzata

### Variabile d'ambiente `HOME`
L'app richiede che la variabile `HOME` sia impostata correttamente. Normalmente è automatico, ma se non funziona:

```bash
# Verifica che HOME sia impostata
echo $HOME
# Dovrebbe mostrare qualcosa come /Users/tuonomeutente
```

Se il problema persiste, lancia l'app dal Terminale:

```bash
open /Applications/Drops.app
```

---

## 🔍 Debug: Dove sono i log?

Se qualcosa non funziona, i log sono in:

```bash
~/.drops/logs/backend.log
```

Leggi gli ultimi 50 righe:

```bash
tail -50 ~/.drops/logs/backend.log
```

---

## 🛡️ Cartella di Configurazione

Tutto è centralizzato in `~/.drops/`:

```
~/.drops/
├── config.json        # Token di autenticazione (privato, creato al primo avvio)
└── logs/
    └── backend.log    # Log persistente dell'app
```

Non toccare `config.json` a meno che non sappia cosa stai facendo. Viene generato automaticamente.

---

## 📍 Stato Attuale: Fase 1 (Stabilizzazione)

Questa versione è in **Fase 1 di Stabilizzazione**. Significa:
- ✅ Funziona per uso quotidiano
- ✅ Supporta 2-5 utenti affidati
- ⏳ Prossimo: Installer migliorato + Auto-update (Fase 2)

Se trovi bug, segnalali con gli ultimi 20 righe di log.

---

## Problemi Comuni

### L'app non parte
**Causa**: Potrebbe essere la porta 8000 occupata  
**Fix**: Controlla i log:
```bash
tail ~/.drops/logs/backend.log | grep "8000\|Errore"
```

### Il token non viene caricato
**Causa**: Possibile permesso mancante su `config.json`  
**Fix**: Riavvia l'app. Se persiste, elimina e ricrea:
```bash
rm ~/.drops/config.json
# Riavvia l'app
```

---

**Domande?** Controlla i log prima di contattarmi. Il 90% dei problemi è nel log.
