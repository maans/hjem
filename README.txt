Måns.dk – fler-sidet visitkort

Forsiden:
- index.html
- Viser kun Apps, Musik og Kontakt
- Kalenderen vises ikke på forsiden

Undersider:
- apps.html: Plan, Tavle, Skriv og Tjek
- musik.html: orkestre samt links til playliste, billeder, kalender og Akustisk-Elektrisk
- playlist.html: indlejret YouTube-playliste
- billeder.html: galleri fra mappen billeder
- kalender.html: separat aktivitetskalender

Sådan opdaterer du kalenderen:
Åbn kalender.html og find:

const events = [
];

Indsæt fx:
{ date: "12. september 2026", title: "Koncert med Birdland Bigband", place: "Aalborg", note: "Kl. 19.30" }

Upload alle HTML-filerne og mappen billeder til roden af repoet hjem.


Opdatering juli 2026:
- Musikoversigten hedder nu "Seneste".
- Solooptrædener er tilføjet ved siden af Akustisk-Elektrisk.
- Billeder kan åbnes i en skærmfyldende visning med klik, pile og Escape.
- Kalenderen er udfyldt ud fra Viggo-ICS-filen.
- Peter Sommer-koncerten og Lottes fødselsdag er ikke medtaget.
- Sankt Hans hos Dorthe er registreret som solooptræden.


Opdatering:
- Appoversigten beskriver nu apps ud fra deres faktiske funktion:
  Plan = samlet undervisningsmiljø
  Tavle = klassisk tavle-, arbejds- og præsentationsmiljø
  Skriv = elevudtalelser og vurderinger
  Tjek = weekend, tilstedeværelse, tjanser, RENG og lister


Kalenderrettelse:
- Kalenderhændelserne er nu skrevet direkte ind i kalender.html.
- De bliver derfor vist, selv hvis JavaScript ikke afvikles.
- Upload kalender.html sammen med de øvrige filer, eller upload hele denne pakke.


Samlet opdatering:
- Forsiden har nu et selvstændigt felt til Om mig.
- om.html indeholder den mellemlange biografi.
- Der er link til https://himmerlandsefterskole.dk.
- Pakken indeholder fortsat apps, musik, playliste, billeder, kalender og billedmappe.
