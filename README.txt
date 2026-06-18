Måns.dk visitkort

Indhold:
- index.html
- billeder/ med startbilleder til slideshow

Brug:
1. Upload index.html til roden af dit GitHub Pages-repo.
2. Upload mappen billeder ved siden af index.html.
3. Ret eventuelt repo-navnet i index.html:

   const githubImageSource = {
     owner: "maans",
     repo: "maans.github.io",
     branch: "main",
     folder: "billeder"
   };

Automatisk slideshow:
Siden forsøger at hente alle billedfiler i mappen billeder via GitHubs offentlige API.
Derfor opdateres slideshowet, når du tilføjer eller fjerner billeder i mappen og committer ændringen.

Hvis GitHub API-listning ikke virker, bruger siden den manuelle fallback-liste nederst i HTML-filen.
