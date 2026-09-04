# Consigli tecnici

- Si consiglia di fare un refresh almeno una volta ogni 6 mesi per mantenere la sessione, evitando così la necessità di effettuare il login digitando email e password.

- Ricordarsi di fare il test della posizione GPS, per essere sicuri che il sistema di rilevamento della posizione geografica del dispositivo funzioni correttamente, così da poter inviare allerte e ricevere allerte vicine.

- Per localizzare il dispositivo mobile dell'utente, il sistema sfrutta prevalentemente il segnale GPS nei luoghi aperti, e le tecniche di triangolazione dei segnali Wi-Fi circostanti nei luoghi chiusi (dove il segnale GPS non viene ricevuto). Per questo motivo, si raccomanda di tenere il Wi-Fi del dispositivo abilitato, al fine di poter inviare allerte accurate e poter ricevere eventuali allerte vicine.

- Al primo avvio o login, l'app chiederà il permesso di ricevere notifiche, il permesso di rilevamento della propria propria posizione GPS "mentre l'app è in uso" e subito dopo anche il permesso di passare alla modalità "consenti sempre". Ecco, ricordarsi di impostare quest'ultima modalità, "consenti sempre", in modo che l'app possa tracciare la posizione GPS approssimativa del dispositivo anche quando essa si trova in background e non in uso.

- Per evitare che il sistema di rilevamento della posizione GPS in background vada in sospensione, è necessario andare nella sezione 'batteria' delle impostazioni di questa app e selezionare 'senza restrizioni'. È possibile raggiungere questa sezione dalle impostazioni generali del dispositivo: Impostazioni -> Applicazioni -> Quidalert -> Batteria -> "Senza restrizioni".

- Per interrompere il processo di tracciamento della posizione in background e non ricevere più notifiche, non è necessario disinstallare l'app, ma è sufficiente effettuare il "logout". Così facendo però non si potrà più ricevere o inviare allerte, fino ad un nuovo eventuale "login".

# Consigli riguardanti le allerte

- Si raccomanda di completare il proprio profilo, al fine di essere contattabili dai capi in caso di necessità, durante un'allerta. Nota: indirizzo, email, telefono e data di nascita non saranno visibili agli utenti normali, ma soltanto ai capi e agli utenti che hanno privilegi amministrativi.

- L'invio di un'allerta prevede la sola compilazione del campo descrizione. L'app sfrutta i sistemi di tracciamento della posizione integrati nel dispositivo per rilevare in automatico la vostra posizione da associare all'allerta. Comunque, per risolvere quei rari problemi di inaccuratezza della localizzazione e per farvi trovare più facilmente, se possibile, sarebbe meglio dare qualche informazione sul posto in cui vi trovate, aggiungendola nella descrizione. Ciò che l'utente inserisce nel campo "descrizione" del modulo di allerta sarà visibile a tutti gli utenti allertati (capo e utenti nelle vicinanze).

- L'utente, dopo l'invio di un'allerta, potrà scrivere ulteriormente nella relativa sezione "messaggi" (presente nella pagina dell'allerta creata), quindi, niente paura se per caso ci si dimentica di scrivere qualcosa nel campo "descrizione". Questi messaggi saranno visibili a tutti gli utenti allertati (capo e utenti nelle vicinanze). Anche il capo dell'allerta potrà scrivere messaggi nella stessa sezione, al fine di dare agli utenti coinvolti eventuali istruzioni utili.

# Voto, affidabilità e punteggio eroe

- Il punteggio di affidabilità va da 0 a 100 (reliability score) e determina l'ampiezza del raggio delle allerte. Esempio: se un utente ha un punteggio di affidabilità uguale a 50, potrà emanare allerte aventi un raggio ridotto della metà rispetto al caso massimo. Coloro che hanno un punteggio di affidabilità uguale a zero, non possono inviare allerte o votare le allerte per un bel po' (non per sempre, in quanto ogni 6 mesi il punteggio di affidabilità viene aumentato di un pochino fino a raggiungere il massimo). Comunque, in casi particolari un utente con privilegi amministrativi può segnalare permanentemente un utente come inaffidabile.

- Il punteggio eroe invece non ha uno scopo particolare, è solo simbolico: è simile al punteggio di affidabilità, ma viene solo aumentato con gli stessi criteri del punteggio di affidabilità (non subisce mai una diminuzione), eccetto rari casi punitivi nei quali viene azzerato. Questo punteggio non ha limite massimo.

- È prevista la possibilità di dare un voto alle allerte create dagli utenti, confermando o negando l'allerta. Alla chiusura dell'allerta da parte del capo, il punteggio di affidabilità di tutti gli utenti coinvolti nell'allerta subisce le seguenti variazioni.

- Se il capo, alla chiusura, conferma l'allerta (trattandosi di allerta vera), il mittente dell'allerta viene premiato, quindi il suo punteggio di affidabilità aumenta. Tutti gli utenti allertati che hanno confermato l'allerta ottengono anch'essi un punteggio positivo, mentre coloro che hanno negato l'allerta (pensando erroneamente che essa fosse falsa), subiscono una penalità (il punteggio di affidabilità diminuisce)

- Se il capo, alla chiusura, nega l'allerta (trattandosi di allerta fasulla), il mittente viene penalizzato con diminuzione del punteggio di affidabilità. Tutti gli utenti allertati che hanno confermato l'allerta falsa vengono penalizzati anche loro, mentre coloro che hanno votato in accordo col capo, negando l'allerta, vengono premiati. Nei casi molto gravi di allerta falsa, il capo può negare l'allerta in maniera "punitiva", azzerando il punteggio di affidabilità del mittente e diminuendo di molto quello degli utenti allertati che hanno confermato l'allerta gravemente falsa, mentre invece gli utenti che hanno negato l'allerta ottengono un bonus alto.

- Ovviamente è possibile non votare, o votare "non so" se non si è sicuri, in modo da non confermare l'allerta e nemmeno "smentirla". In tal caso, non ci sarà nessuna penalità e nessun premio alla chiusura dell'allerta.
