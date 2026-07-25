---
name: spotify-drops-library
description: Importare tutti i brani preferiti Spotify come catalogo, cercare candidati esterni, avviare download autorizzati tramite Drops e organizzare MP3/FLAC per genere in Music Gianco. Usare quando Giancarlo chiede di sincronizzare preferiti Spotify, preparare musica per chiavetta o riordinare libreria Drops.
---

# Spotify Drops Library

Usare backend locale Drops. Spotify fornisce solo metadati; non trattare URL Spotify come sorgenti audio.

## Flusso

1. Leggere `references/setup.md` se account Spotify non risulta collegato.
2. Aprire `GET /spotify/connect` nel browser; endpoint reindirizza al login Spotify PKCE.
3. Chiamare `POST /spotify/import` una volta. Endpoint pagina tutti i preferiti e salva catalogo in `~/.drops/spotify-library.json`.
4. Leggere catalogo con `GET /spotify/library?offset=0&limit=100`.
5. Per brano richiesto, chiamare `POST /spotify/library/{spotify_id}/candidates`.
6. Mostrare candidato, canale, durata e URL. Non scegliere versione ambigua, cover, live o remix senza conferma.
7. Avviare `POST /download` includendo `spotify_track_id`, candidato `url`, formato audio e `rights_confirmed: true` solo dopo conferma utente di diritti/autorizzazione.
8. Controllare `GET /status/{job_id}`. A completamento riportare `library_path`.

## Regole

- Non scaricare audio da Spotify.
- Non impostare `rights_confirmed` per conto utente.
- Non approvare automaticamente intero catalogo.
- Conservare attribuzione tramite `spotify_url` nel catalogo.
- Usare `genre_folder` calcolato; lasciare generi incerti in `Altri Generi`.
- Non eliminare file esistenti. Drops aggiunge suffisso numerico in caso duplicato.
- Destinazione predefinita: `~/Documents/Music Gianco/<Genere>/`.
