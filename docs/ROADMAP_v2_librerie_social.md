# Roadmap v2 — Aggregatore libreria da account social

> Documento tecnico di approfondimento. Roadmap prodotto principale:
> `PRODUCT_ROADMAP.md`.

> Linea di sviluppo dedicata: collegare un account esterno, leggere i "preferiti/like",
> trovare una sorgente scaricabile, e **scaricare + organizzare per genere** in
> `Music Gianco/<Genere>/`. Sempre con conferma esplicita dei diritti.

Il pattern è identico per tutte e tre le piattaforme; cambia solo la fonte dei preferiti.

```
Collega account → leggi preferiti/like → risolvi genere (MusicBrainz)
→ cerca sorgente scaricabile → CONFERMA DIRITTI → download → Music Gianco/<Genere>/
```

---

## v2.0 — Spotify  *(in corso)*

Collegamento account Spotify manuale, import dei preferiti, generi, download e organizzazione.

**Stato al 24 luglio 2026:** logica completa e **collaudata** come endpoint backend
(`/spotify/*`) + script di supporto (`diagnose_spotify.py`, `analyze_genres.py`,
`batch_download.py`). Auth risolta, 722 preferiti importati, generi via MusicBrainz,
regole di genere ampliate.

**NON ancora integrata nell'UI dell'app Drops** — al momento si opera da terminale/curl,
e **va bene così**: non integriamo ancora nell'app.

**Per la "v2.0" vera (futuro):** portare il flusso dentro l'app — UI in `index.html`
(pulsante "Collega Spotify", lista preferiti, selezione, avvio download) costruita
sopra gli endpoint `/spotify/*` che **esistono già**. Non richiede nuova logica backend,
solo il frontend. Da valutare insieme alla questione architetturale del WebView Tauri
(vedi `CLAUDE.md`).

---

## v2.1 — SoundCloud

Stesso flusso: collega profilo SoundCloud → likes/preferiti → download + organizzazione.

**Nota tecnica:** yt-dlp **scarica già** da SoundCloud (collaudato, vedi test in
`HANDOFF_SPOTIFY_DROPS.md`). La parte nuova è **leggere i "likes"** di un profilo:
l'API pubblica SoundCloud è di fatto chiusa a nuove app, quindi va valutato un
workaround (es. scraping autorizzato del proprio profilo, o export). Il resto della
pipeline (genere → download → cartella) si riusa identico.

---

## v2.2 — YouTube profile

Stesso flusso: profilo YouTube → video "Mi piace" / playlist → download + organizzazione.

**Nota tecnica:** il download è già gestito da yt-dlp. La parte nuova è **leggere
liked videos / playlist**: richiede **YouTube Data API v3** con OAuth (scope
`youtube.readonly`). Il resto della pipeline si riusa identico.

---

## Principi trasversali (validi per tutte le versioni)

- **Conferma diritti obbligatoria** prima di ogni download (`rights_confirmed`).
- **Genere via MusicBrainz** come fonte unica: nessuna quota, cache su disco, resumibile.
- **Attribuzione:** conservare sempre l'URL sorgente nel catalogo.
- **Organizzazione:** destinazione finale `Music Gianco/<Genere>/Artista - Titolo.<ext>`.
- **Riuso:** la logica candidati/download/organizzazione è comune; ogni nuova
piattaforma aggiunge solo il "lettore di preferiti".

---

## v2.x — Analytics sviluppatore e controllo prodotto

Dashboard privata per capire stabilità, adozione funzioni e priorità roadmap.

**Fase tecnica iniziale, opt-in:**

- ID installazione casuale, non legato a hardware/account;
- versione app, sistema operativo e architettura;
- eventi download iniziato/riuscito/fallito;
- sorgente aggregata, formato, qualità e categoria errore;
- uso coda, cartella personalizzata, taglio video e aggiornamenti;
- dashboard privata con utenti attivi, versioni, errori e feature usage.

**Escluso dal consenso analytics standard:** URL, titoli, artisti, account e
percorsi locali. Eventuale studio musicale richiede consenso separato,
informativa specifica, conservazione limitata e cancellazione dati.

Architettura prevista:

```text
Drops → consenso locale → API eventi → database → dashboard privata
```

Updater resta separato da analytics: controllare aggiornamenti non trasmette
cronologia download.
