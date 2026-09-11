# App info

Questa app è utile per inviare richieste di allerta al fine di ricevere aiuto: l'utente, compilando un semplice modulo di richiesta, può inviare un'allerta al server, il quale la propagherà inviando una notifica al capo dei soccorsi presente nella zona e agli utenti geograficamente vicini.

Per poter usare questa applicazione, devi fare le seguenti cose:

- Recarsi presso l'autorità competente del territorio al fine di dichiarare (autorizzare) il proprio indirizzo email.

- Dopo aver fatto questo, si può effettuare la registrazione del proprio account, usando questa app.

- Infine, effettuare il Login.

## Accesso alla posizione

Per inviare una richiesta di aiuto (un'allerta), l'app accederà alla tua posizione GPS istantaneamente. 

Viceversa, per ricevere le eventuali allerte provenienti da altri utenti presenti nelle vicinanze, l'app ha bisogno dell'abilitazione delle notifiche e di aggiornare periodicamente la tua posizione in background, anche quando l'applicazione è stata nascosta o chiusa.  
Verranno quindi chieste all'utente le seguenti autorizzazioni:
- Consenti notifiche
- Posizione GPS esatta (e poi "Consenti sempre")
- Consenti rilevamento attività fisica
- Verrà chiesto di impostare la modalità batteria "Senza restrizioni" nel pannello delle impostazioni dell'app.

Questo processo di tracciamento in background si avvierà automaticamente solo dopo aver effettuato correttamente il login, e verrà interrotto immediatamente se deciderai di disconnetterti dal server (logout).

Nota: al fine di garantire il massimo risparmio della batteria, quando è fermo il sistema non interroga quasi mai il sistema di geolocalizzazione, mentre quando è in movimento è ottimizzato per rilevare solo le posizioni GPS relative a spostamenti significativi (almeno 250 metri). In aggiunta, la distanza percorsa necessaria per far scattare il rilevamento gps, diventa progressivamente più grande all'aumentare della velocità, così ad alte velocità il dispositivo non interrogherà di continuo il gps, ma solo di tanto in tanto.

Nota: il server memorizzerà temporaneamente, per ciascun utente, solo l'ultima posizione GPS ricevuta, non l'intera cronologia di tracciamento. Se l'utente effettua il logout, la sua posizione GPS non verrà più aggiornata e, dopo alcuni giorni, il server eliminerà automaticamente questa vecchia posizione.

## [Login](/login)

## [Registrazione account](/register)

## [Termini legali](/terms)
