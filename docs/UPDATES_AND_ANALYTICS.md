# Drops — aggiornamenti e analytics

## Incidente UI vecchia dopo installazione 1.3.0

Drops contiene due processi:

1. app Tauri, che mostra finestra;
2. backend locale PyInstaller, che serve UI su `127.0.0.1:8000`.

Backend veniva terminato solo durante evento Tauri `RunEvent::Exit`. Se app
veniva sostituita, terminata forzatamente o chiusa fuori dal normale ciclo vita,
evento poteva non arrivare. Backend restava sulla porta 8000. Nuova app avviava
nuovo backend, ma questo non poteva occupare porta già usata; WebView finiva
quindi sulla UI incorporata nel backend vecchio.

## Correzioni introdotte

- Tauri passa `DROPS_PARENT_PID` al backend.
- Backend controlla ogni 2 secondi esistenza processo padre e termina se manca.
- Plugin ufficiale `tauri-plugin-single-instance` impedisce doppie istanze e
  riporta in primo piano finestra già aperta.
- Endpoint `/app-info` espone versione backend realmente attiva.
- Endpoint `/update/check` legge ultima Release pubblica dal repository GitHub.
- UI mostra banner quando versione GitHub supera versione installata.
- UI mostra sempre versione corrente nello stesso spazio del banner.

## Aggiornamento automatico — passo successivo

Banner attuale apre pagina Release. Installazione automatica richiede updater
ufficiale Tauri e artefatti firmati.

Il controllo legge solo ultima **GitHub Release pubblicata**. Un normale push sul
branch non basta. Tag/versione e workflow Release devono creare pubblicazione;
alla successiva apertura (o dopo scadenza cache di un'ora) app vede nuova
versione. Versione 1.3 apre pagina Release ma non scarica/installa da sola.

Checklist:

1. generare coppia chiavi updater Tauri;
2. conservare chiave privata solo nei GitHub Actions Secrets e in backup sicuro;
3. inserire chiave pubblica in `tauri.conf.json`;
4. abilitare `createUpdaterArtifacts`;
5. produrre `latest.json` e file `.sig` per macOS e Windows;
6. mostrare conferma utente, scaricare, installare e rilanciare;
7. testare aggiornamento da versione N a N+1 con download attivo e app chiusa.

Perdita chiave privata impedirebbe aggiornamenti futuri alle installazioni già
distribuite. Non committare mai chiave privata.

## Analytics — principi prima di implementazione

Analytics devono essere separati da updater. Controllo aggiornamenti non deve
trasmettere cronologia download.

Prima versione consigliata, solo con consenso esplicito e opt-out:

- installazione anonima casuale;
- versione app, sistema operativo e architettura;
- avvio app;
- download iniziato/riuscito/fallito;
- sorgente aggregata (`youtube`, `soundcloud`);
- formato e qualità;
- durata e categoria errore;
- uso coda, cartella personalizzata e taglio video.

Non raccogliere per default:

- URL completo;
- titolo brano, artista o query;
- percorso cartella;
- account Spotify;
- indirizzo IP conservato;
- identificatori hardware.

Titoli e brani costituiscono profilo comportamentale. Raccolta richiede finalità
chiara, consenso granulare, informativa privacy, durata conservazione, accesso e
cancellazione dati. Se ricerca catalogo serve davvero, creare programma
facoltativo separato con consenso specifico.
