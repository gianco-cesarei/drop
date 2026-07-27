# Drops — Product Roadmap

Fonte principale per priorità prodotto. Le versioni indicano ordine e confini,
non date rigide. Roadmap tecniche collegate approfondiscono singole aree.

## Visione

Drops evolve in due linee:

1. **V1 - locale:** scaricare, organizzare, ascoltare e preparare musica presente
   sul computer.
2. **V2 - connessa:** collegare librerie esterne, importare preferiti e usare
   intelligence di prodotto.

Sequenza:

```text
Download affidabile
→ distribuzione e aggiornamenti
→ metadati e libreria locale
→ player
→ playlist e preparazione DJ
→ account esterni
```

---

## V1 — Download, libreria locale e ascolto

### v1.3 — Coda, destinazione, rebranding e update check

Stato: **in preparazione per Release**.

- coda multi-link, massimo 100 elementi e 3 download simultanei;
- salvataggio in Download o cartella scelta;
- MP3 predefinito e modalità Video separata;
- taglio clip disponibile solo per Video;
- rebranding verde `#22C55E` e nuova icona Drops v3;
- versione sempre visibile e avviso nuova GitHub Release;
- watchdog backend e singola istanza Tauri;
- build macOS/Windows e guide installazione.

Gate Release:

- smoke test Mac e Windows;
- prova download YouTube e SoundCloud;
- verifica cartella scelta, coda e clip Video;
- commit, tag `v1.3.0`, workflow e Release GitHub.

### v1.4 — Distribuzione e affidabilità

Obiettivo: utenti ricevono fix senza reinstallazioni manuali e capiscono errori.

- updater Tauri firmato con download, installazione e riavvio;
- firma/notarizzazione macOS;
- aggiornamento Windows in modalità passiva;
- annulla e riprova download;
- rimuovi e riordina elementi coda;
- gestione duplicati e nomi file;
- pagina Impostazioni;
- diagnostica/log esportabile;
- categorie errore leggibili;
- aggiornamento controllato yt-dlp.

Gate:

- test aggiornamento reale N → N+1 su Mac e Windows;
- nessun backend orfano;
- download attivo gestito prima dell’aggiornamento;
- chiave updater privata conservata solo in Secrets e backup sicuro.

### v1.5 — Metadati e libreria locale

Obiettivo: trasformare file scaricati in catalogo interrogabile.

- indicizzazione cartelle selezionate;
- database locale;
- titolo, artista, album, genere e cover;
- scrittura/correzione tag ID3;
- ricerca e filtri;
- file mancanti e duplicati;
- aggiornamento incrementale dopo ogni download;
- cartelle monitorate configurabili;
- cronologia persistente.

Gate:

- scansione grande libreria senza bloccare UI;
- re-scan incrementale;
- nessuna modifica distruttiva ai file senza conferma.

### v1.6 — Lettore musicale

Obiettivo: ascoltare libreria senza uscire da Drops.

- mini-player persistente;
- play, pausa, seek e volume;
- precedente/successivo;
- coda ascolto;
- shuffle e repeat;
- riproduzione da ricerca/libreria;
- memoria ultimo brano e posizione;
- supporto MP3, FLAC, M4A e formati compatibili.

### v1.7 — Playlist e organizzazione DJ

Obiettivo: passare da libreria a preparazione musicale.

- playlist manuali;
- smart playlist;
- preferiti locali;
- filtri genere, BPM, tonalità e anno;
- esportazione playlist/cartelle su chiavetta;
- verifica file incompatibili;
- normalizzazione struttura e nomi.

### v1.8 — Strumenti DJ

Obiettivo: preparare set senza trasformare Drops in software da performance.

- analisi BPM e tonalità;
- waveform;
- cue point;
- preparazione set;
- esportazioni compatibili da valutare per Rekordbox/Serato;
- crossfade solo dopo validazione utenti.

Fuori scope V1: mixing live completo, controller MIDI e sostituzione DAW/DJ app.

---

## V2 — Librerie esterne e intelligence

### v2.0 — Spotify

- collegamento account;
- import preferiti;
- generi e catalogo;
- ricerca sorgenti candidate;
- conferma diritti;
- download e organizzazione locale.

Backend esistente va integrato nell’interfaccia.

### v2.1 — SoundCloud

- collegamento profilo o import autorizzato;
- lettura likes;
- riuso pipeline catalogo/download;
- gestione limiti API o export dati.

### v2.2 — YouTube

- OAuth YouTube Data API;
- playlist e video piaciuti;
- riuso pipeline catalogo/download.

### v2.x — Analytics sviluppatore

Obiettivo: decidere roadmap usando stabilità e feature usage, non sorvegliare
gusti musicali.

- consenso esplicito e opt-out;
- ID installazione casuale;
- versione, OS e architettura;
- download iniziato/riuscito/fallito;
- sorgente aggregata, formato, qualità e categoria errore;
- uso coda, cartelle, clip, player e aggiornamenti;
- dashboard privata;
- retention e versioni attive.

Esclusi dal consenso standard:

- URL completi;
- titoli e artisti;
- account;
- percorsi locali;
- identificatori hardware.

Eventuale ricerca musicale richiede consenso separato e informativa specifica.

---

## Regole di priorità

Nuova funzione entra solo se:

1. problema utente chiaro;
2. dipendenze precedenti complete;
3. test e distribuzione sostenibili;
4. nessun aumento inutile di rischio legale/privacy;
5. interfaccia resta semplice.

Documenti collegati:

- `ROADMAP_v2_librerie_social.md` — dettaglio tecnico account esterni;
- `UPDATES_AND_ANALYTICS.md` — updater, incidente backend e analytics;
- `RELEASE.md` — procedura Release;
- `DISTRIBUTION.md` — firma e distribuzione.
