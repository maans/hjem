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
