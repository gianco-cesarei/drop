# Handoff: Spotify preferiti → Drops → Music Gianco

Aggiornato: 24 luglio 2026.

## Obiettivo

Leggere tutti i brani salvati nei “Preferiti” dell’account Spotify di Giancarlo,
senza scaricare audio da Spotify. Spotify viene usato solo come catalogo
artist/titolo/album/URL. Drops cerca poi una sorgente esterna supportata e, solo
dopo conferma esplicita dei diritti da parte dell’utente, scarica il file e lo
organizza qui:

```text
/Users/gianco/Documents/Music Gianco/<Genere>/Artista - Titolo.mp3
```

Cartella progetto:

```text
/Users/gianco/Documents/Claude/Projects/mp3-downloader
```

La cartella musica è separata dal progetto.

## Stato attuale

- Backend Drops avviabile e funzionante su `http://127.0.0.1:8000`.
- OAuth Spotify PKCE funzionante.
- Callback funzionante e mostra `Spotify collegato a Drops`.
- Token Spotify ottenuto e salvato localmente.
- **403 RISOLTO (24 luglio 2026).** `/v1/me` e `/v1/me/tracks` ora rispondono
  correttamente. Account autenticato: `31bnpr6snvsmbihbkfb6w2wkvzvq`
  (Giancarlo Cesarei).

### Come è stato risolto il 403

Il 403 `"The user is not registered for this application"` NON dipendeva dalla
config Spotify (Web API era attiva, redirect URI corretto, account presente in
User Management) né dal codice Drops. Causa reale: **token stantìo in
`~/.drops/spotify-token.json`** generato da una vecchia sessione/account; la
logica di refresh continuava a rinnovare l'identità sbagliata, quindi ogni nuovo
"login" restava bloccato sull'account errato.

Fix applicato:
1. Aggiunto `show_dialog=true` ai parametri OAuth in
   `spotify_agent.create_authorization()` → Spotify mostra sempre il selettore
   account e non riusa in silenzio una sessione errata.
2. Reset stato locale:
   `rm ~/.drops/spotify-token.json ~/.drops/spotify-auth-state.json`
3. Nuovo login pulito da `/spotify/connect`, scegliendo esplicitamente
   l'account corretto sulla schermata di consenso.
4. Verifica con `backend/diagnose_spotify.py` (vedi sotto).

### Import completato e verificato (25 luglio 2026)

- `POST /spotify/import` COMPLETATO: **723 preferiti** presenti in
  `~/.drops/spotify-library.json`, tutti con genere risolto.
- Catalogo verificato alle `00:17:19`: 558047 byte.
- **I generi NON vengono più da Spotify** (la quota Development Mode dava
  `429 QUOTA_EXCEEDED` su ~780 chiamate `/v1/artists/{id}`). Ora arrivano da
  **MusicBrainz** per nome artista: nessuna auth, nessuna quota, ~1 req/s, cache
  su disco `~/.drops/spotify-artist-genres.json`, import resumibile a lotti di
  200 (rilanciare finché `genres_complete:true`). Spotify resta usato solo per
  leggere i preferiti (`/me/tracks`).
- Nota mappatura: New Order cade in "House" per precedenza delle `GENRE_RULES`
  (tag misti synth/house). Affinare l'ordine delle regole se serve.

### Aperto ora — prossima fase: candidati + download + scoperta

- Nessun download ancora avviato dal flusso Spotify.
- Flusso previsto: `POST /spotify/library/{track_id}/candidates` per trovare una
  sorgente esterna, poi `POST /download` con `spotify_track_id` +
  `rights_confirmed:true` (solo dopo conferma esplicita) → file in
  `Music Gianco/<Genere>/`.
- Obiettivo secondario: scoprire brani nuovi coerenti col profilo
  (`profilo_musicale.md`) e aggiungerli alla selezione.

### Strumento di diagnosi

`backend/diagnose_spotify.py` — script standalone (solo stdlib, no `yt_dlp`) che
chiama `/me` e `/me/tracks` per isolare il livello di un eventuale blocco. Non
stampa mai il token. Va lanciato col venv per avere i certificati SSL:
`.venv/bin/python3.11 backend/diagnose_spotify.py`.

## Configurazione Spotify eseguita

App Spotify Developer:

```text
Nome: DROP
Modalità: Development mode
Client ID pubblico: 7b99b9653fba45ae974edcd553312387
Redirect URI: http://127.0.0.1:8000/spotify/callback
Scope richiesto: user-library-read
```

Azioni già fatte:

1. App creata nel Spotify Developer Dashboard.
2. Redirect URI registrato esattamente.
3. Account Spotify Premium corretto usato per login.
4. Account aggiunto in `User Management` della app.
5. Utente conferma che email account e allowlist coincidono.
6. Web API indicata come abilitata dall’utente.
7. Backend riavviato con Client ID corretto.
8. Nuovo login OAuth completato.
9. Callback completata.
10. Nuovo `POST /spotify/import` eseguito.
11. Spotify continua a restituire stesso 403.

Nota storica: in uno screenshot precedente, `APIs used` mostrava `-`. È stato
chiesto di modificare app, selezionare `Web API`, accettare termini e salvare.
Prima di altro debug, verificare visivamente che adesso `APIs used` mostri
realmente `Web API`.

Un tentativo precedente usava per errore il Client ID racchiuso fra `**`, quindi
Spotify mostrava `client_id: Invalid`. Problema corretto: variabile deve
contenere solo valore puro, senza asterischi.

## Avvio corretto

Da Terminale:

```bash
cd "/Users/gianco/Documents/Claude/Projects/mp3-downloader"
export SPOTIFY_CLIENT_ID="7b99b9653fba45ae974edcd553312387"
export SPOTIFY_REDIRECT_URI="http://127.0.0.1:8000/spotify/callback"
export DROPS_MUSIC_DIR="/Users/gianco/Documents/Music Gianco"
./start.sh
```

Non serve Client Secret: implementazione usa Authorization Code con PKCE.
Non inserire token, authorization code o Client Secret nel repository.

Poi:

1. Aprire `http://127.0.0.1:8000/spotify/connect`.
2. Completare login Spotify.
3. Verificare pagina `Spotify collegato a Drops`.
4. Aprire `http://127.0.0.1:8000/docs`.
5. Eseguire `POST /spotify/import`.
6. Se riesce, verificare `GET /spotify/library?offset=0&limit=100`.

## File implementati o modificati

### `backend/spotify_agent.py`

Implementa:

- OAuth Spotify Authorization Code con PKCE.
- Refresh token.
- Import paginato da `/v1/me/tracks`.
- Lettura generi via chiamate singole `/v1/artists/{id}`.
- Catalogo locale.
- Mappatura genere → sottocartella.
- Ricerca candidati esterni.
- Contesto di download autorizzato.

Le chiamate singole agli artisti sono intenzionali: nel Development Mode Spotify
2026 ha rimosso endpoint batch artist per nuove app.

### `backend/main.py`

Endpoint aggiunti:

```text
GET  /spotify/connect
GET  /spotify/callback
POST /spotify/import
GET  /spotify/library?offset=0&limit=100
POST /spotify/library/{track_id}/candidates
```

`POST /download` supporta:

```json
{
  "spotify_track_id": "ID_SPOTIFY",
  "rights_confirmed": true
}
```

`rights_confirmed: true` deve essere inviato solo dopo conferma esplicita
dell’utente. A fine download, risposta include `library_path`.

### Skill locale

```text
skills/spotify-drops-library/SKILL.md
skills/spotify-drops-library/references/setup.md
```

### Documentazione

`README.md` contiene setup sintetico.

## Stato locale persistente

Fuori dal repository:

```text
~/.drops/spotify-token.json
~/.drops/spotify-auth-state.json
~/.drops/spotify-library.json
```

- Token file esiste dopo callback riuscita.
- Catalogo contiene attualmente 723 preferiti importati.
- Non stampare contenuto token nei log o nella chat.

Per forzare nuovo consenso, usare di nuovo `/spotify/connect`; non riutilizzare
manualmente vecchi parametri `code` o `state` della callback.

## Test SoundCloud già riuscito

Drops supporta SoundCloud tramite yt-dlp. Test autorizzato dall’utente:

```text
URL:
https://soundcloud.com/blackcherry-podcast/the-flirts-passion-black

File:
/Users/gianco/Documents/Music Gianco/Italo Disco - Hi-NRG/The Flirts - Passion (Black Cherry sweety Edit).mp3
```

Download completato, circa 8.8 MB, metadati incorporati. Questo conferma che
downloader, SoundCloud e destinazione `Music Gianco` funzionano.

## Diagnosi solo se il 403 ricompare

Il 403 è risolto. Non trattarlo come blocco attuale. In caso di regressione:

1. Provare endpoint innocuo `/v1/me` con token corrente per identificare account
   Spotify effettivamente autenticato; non esporre token.
2. Confrontare ID/account restituito da `/v1/me` con utente previsto.
3. Cancellare token e stato OAuth stantii, quindi rifare `/spotify/connect`.
4. Riprovare `/v1/me/tracks?limit=1`.
5. Se `/v1/me` funziona ma `/v1/me/tracks` resta 403, blocco è allowlist/quota
   Spotify, non codice Drops.
6. Se Spotify non sblocca, usare esportazione dati Spotify JSON come fallback:
   importare metadata dei preferiti senza Web API e continuare stesso flusso
   candidati/download autorizzati.

## Vincoli

- Non scaricare audio da Spotify.
- Non aggirare DRM o autenticazione.
- Non avviare download senza conferma esplicita dei diritti.
- Preservare `spotify_url` nel catalogo per attribuzione.
- Destinazione finale: `Music Gianco/<Genere>/`.
- Obiettivo secondario progetto: scoprire brani compatibili coi gusti di
  Giancarlo e aggiungerli alla selezione musicale.
