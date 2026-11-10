# Sito di geoLAB: istruzioni per Claude

Questo repository contiene il sito di geoLAB, Laboratory of Forest Geomatics (Università di Firenze), online su https://geolabforest.com. È un sito statico: i testi sono file Markdown in `content/`, uno script Python (`build.py`, solo libreria standard) li trasforma in pagine nella cartella `docs/`. La build e la pubblicazione sono automatiche: a ogni unione su `main` GitHub Actions (`.github/workflows/pages.yml`) ricostruisce il sito e lo pubblica su GitHub Pages. `docs/` non è nel repository, tranne `docs/media/`.

Chi ti usa è un membro del laboratorio che vuole aggiungere o aggiornare contenuti. Segui queste regole prima di toccare qualsiasi file.

## Regole non negoziabili

1. **Il sito è solo in inglese.** Titoli, testi, nomi di sezione, testi alternativi delle immagini. Niente testo italiano, nemmeno nelle immagini (slide, tabelle, locandine in italiano non vanno pubblicate). I nomi propri di enti, programmi ed eventi restano in originale, con una spiegazione in inglese. `build.py` avvisa se trova testo che sembra italiano: correggi prima di proseguire.
2. **Solo fatti pubblici e verificabili.** Usa i materiali che l'utente fornisce. Mai budget, deliverable non ancora pubblici, risultati non pubblicati, articoli sotto embargo, dati di partner non autorizzati. Non inventare numeri, nomi, date, risultati o link: se manca un dato, chiedilo.
3. **Progetti finanziati dall'UE.** Ogni pagina di un progetto finanziato (e ogni news su un progetto finanziato) riporta l'emblema UE e la dicitura completa di finanziamento: nell'intestazione del file `emblem: yes` e `funding: ...` con il testo esatto previsto dal Grant Agreement (per i progetti dell'agenzia REA: "Funded by the European Union. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or the European Research Executive Agency. Neither the European Union nor the granting authority can be held responsible for them."). Per progetti di altre agenzie (ad esempio LIFE, CINEA, HaDEA) chiedi il testo corretto all'utente.
4. **Persone.** Pubblica nomi, ruoli e foto solo con il consenso delle persone. Non pubblicare telefoni o email di terzi. Le email dei colleghi si scrivono `nome.cognome(at)unifi.it`.
5. **Nessuna credenziale.** Non chiedere né inserire password, token o chiavi. L'accesso a GitHub lo fa l'utente nel proprio browser.
6. **Tono sobrio e fattuale**, come un buon comunicato scientifico: frasi chiare con il soggetto esplicito, numeri specifici (partner, paesi, date) al posto degli aggettivi, nessun linguaggio promozionale.

## Come è organizzato

- `content/projects/`, `content/news/`, `content/publications/`, `content/research/`, `content/courses/`, `content/pages/`, `content/people/`: un file `.md` per contenuto. `content/about.md` è il testo della home.
- `static/`: CSS, loghi e immagini fisse del sito.
- `docs/media/AAAA/MM/`: immagini degli articoli. È l'unica parte di `docs/` che si modifica a mano.
- `docs/` (tutto il resto): generato da `build.py` sul tuo computer solo per l'anteprima (Git lo ignora). Non modificarlo a mano.
- `.github/`: workflow di pubblicazione e file `CODEOWNERS`. Non toccarli senza chiedere a Gherardo.
- `tools/`: script di servizio (importazione dal vecchio WordPress, compressione immagini).

Ogni file ha in testa un'intestazione tra due righe `---`:

```
---
title: Titolo in inglese
date: 2026-11-03            (news e pubblicazioni; per i progetti si usa year: 2026)
subtitle: Una riga di sottotitolo   (facoltativo)
logo: /img/logo/nome.png            (progetti, facoltativo)
image: /media/2026/11/foto.jpg      (immagine di anteprima, facoltativa)
alt: Testo alternativo dell'immagine, in inglese
emblem: yes                         (progetti finanziati UE)
funding: testo di finanziamento     (progetti finanziati UE)
---
```

Il corpo è Markdown semplice (paragrafi, `## titoli`, elenchi con `- `, `**grassetto**`, `[testo](https://...)`, `![alt](/media/...)`). Per un nuovo contenuto parti da un file simile già presente: `content/news/2026-11-03-nextbon-kickoff.md` per una news con emblema UE, `content/projects/monifun.md` per un progetto.

Il nome del file è l'indirizzo: `content/news/2026-11-20-titolo-breve.md` diventa `/news/2026-11-20-titolo-breve/`. Usa minuscole e trattini.

**Pagina People** (`content/pages/people.md`): è HTML dentro Markdown. Per aggiungere una persona copia una riga `<tr>...</tr>` esistente nella tabella "Team" e cambia nome, ruolo, email e foto (foto quadrata, circa 480 px, in `docs/media/AAAA/MM/`).

**Contenuti importati dal vecchio sito** (`source: wordpress` nell'intestazione): si possono modificare, ma cambia prima `source: wordpress` in `source: wordpress-edited`, altrimenti una futura importazione li sovrascrive.

## Immagini

- Salvale in `docs/media/AAAA/MM/nome-chiaro.jpg`, lato lungo massimo 1600 px (poi `python tools/optimize_media.py` le comprime), e citale con `/media/AAAA/MM/nome-chiaro.jpg`.
- Ogni immagine ha un testo alternativo in inglese che descrive ciò che si vede.
- Foto con persone riconoscibili: solo se l'utente conferma il consenso. Loghi e emblema UE: non modificarli.

## Come si lavora (flusso obbligatorio)

Non si scrive mai direttamente su `main`: ogni modifica passa da un ramo e da una pull request, che Gherardo Chirici controlla e approva.

1. `git pull` sul ramo `main`, poi un ramo nuovo: `git switch -c nome/argomento` (ad esempio `rossi/news-nextbon`).
2. Modifica i file in `content/` (e `static/`, `docs/media/` se servono immagini).
3. Anteprima: `python build.py` (deve finire senza errori e senza avvisi di testo italiano), poi `python -m http.server 8000 --directory docs` e apri http://localhost:8000. Controlla le pagine toccate. Ferma il server quando hai finito.
4. Controlla con `git status`: devono risultare modificati solo file in `content/`, `static/`, `docs/media/` (il resto di `docs/` è ignorato da Git).
5. Commit solo di quelle cartelle: `git add content static docs/media`, messaggio in inglese, breve e descrittivo. Per l'email dell'autore usa quella `noreply` di GitHub (`git config user.email "TUO-NOME-UTENTE@users.noreply.github.com"`), non l'email di ateneo: il repository è pubblico.
6. `git push -u origin nome/argomento` (la prima volta si apre il browser per l'accesso a GitHub: la password la inserisce l'utente). Poi apri la pull request su GitHub e avvisa Gherardo Chirici.
7. Sulla pull request GitHub Actions esegue `tools/check_pr.py` (lingua, emblema UE, email e telefoni, immagini, file fuori area) e ricostruisce il sito: puoi lanciare lo stesso controllo in locale con `python -I tools/check_pr.py --base main`. Se fallisce, leggi l'errore e correggi; gli avvisi li valuta chi approva. Dopo l'approvazione di Gherardo e l'unione su `main` il sito si ricostruisce e si pubblica da solo (in un paio di minuti): chi propone la modifica non deve fare altro.

Se qualcosa non torna (build che fallisce, conflitti, dubbi su un dato), fermati e chiedi all'utente invece di forzare.
