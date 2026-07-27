# Drops — installazione macOS

## Esperienza normale: versione firmata e notarizzata

1. Apri `Drops.dmg`.
2. Trascina `Drops.app` in `Applicazioni`.
3. Apri Drops da `Applicazioni`.
4. macOS può chiedere accesso a `Download`, `Documenti`, unità esterne o rete
   locale. Concedi solo permessi necessari alle funzioni che vuoi usare.

Una release pubblica deve essere firmata con certificato Apple Developer ID e
notarizzata da Apple. In quel caso non serve modificare impostazioni di
sicurezza o eseguire comandi nel Terminale.

## Build locale non notarizzata

Una build locale può mostrare:

> Apple non può verificare che Drops sia priva di malware.

Questo avviso indica che la build non è stata notarizzata. Non dimostra né
esclude presenza di malware.

Apri una build locale solo se sai chi l’ha compilata e hai verificato la sua
provenienza:

1. Sposta `Drops.app` in `Applicazioni`.
2. Nel Finder, fai click destro su `Drops.app`.
3. Seleziona `Apri`.
4. Conferma `Apri`.

Se il pulsante non compare:

1. Prova ad aprire Drops una volta.
2. Apri `Impostazioni di Sistema`.
3. Vai in `Privacy e sicurezza`.
4. Cerca messaggio relativo a Drops.
5. Se la provenienza è verificata, premi `Apri comunque`.
6. Conferma con password o Touch ID.

Non disattivare Gatekeeper. Non usare comandi globali come
`spctl --master-disable`. Non rimuovere attributi di quarantena da cartelle
generiche.

