# data handling

How the project handles the personal information inside the grant records. The brief (section 5.5)
asks for this document before any ingestion code is written. We are a bit late with it: the text
extractor and the data inventory already exist and read the raw forms directly. From this point on,
everything downstream of ingestion should read the pseudonymised copies described below, not `data/raw`
or `data/synthetic/raw`.

We only have the synthetic dataset (`data/synthetic/`), and every name in it is fake. We still treat
those names as if they were real, so the pipeline does the right thing if real records ever arrive.

## what personal information is in the forms

We checked every table cell and paragraph in all 765 synthetic forms. Names only appear in these places:

| Form | Where | Who | Pseudonym |
|---|---|---|---|
| Proposal | "Principal investigator / الباحث الرئيس" row | the PI | `RESEARCHER-###` |
| Proposal | "Name / الاسم" column of the research team table | PI and co-investigators | `RESEARCHER-###` |
| Proposal | "Researcher / الباحث" column of the timetable | team member assigned to each task | `RESEARCHER-###` |
| Review | "Reviewer / المحكم" row | the reviewer | `REVIEWER-##` |
| Final report | "Submitted by / مقدم من" row | the PI | `RESEARCHER-###` |
| Assessment | none | | |
| Progress report | none | | |

Names are written as `Dr. Fake-Ahmed Alpha` in English forms and `د. أحمد الوهمي` in Arabic forms.
Other things that could identify someone, such as department, college or the grant ID, are kept. Without them
the portfolio map and the round comparison cannot be done, and on their own they don't name a person.

## how pseudonymisation works

`app/ingestion/pseudonymiser.py` runs first, before anything else reads the forms.

0. It goes through every form in the raw folder (proposals, assessments, reviews, progress reports,
   final reports) and collects names from the labelled fields in the table above.
1. Each new person gets the next free code: `RESEARCHER-001`, `RESEARCHER-002`, … for researchers and
   `REVIEWER-01`, `REVIEWER-02`, … for reviewers. Researchers and reviewers are numbered separately.
   A person who is a researcher on one proposal and a reviewer on another gets two codes that are not
   linked anywhere in the outputs.
2. Names are matched after removing titles (`Dr.`, `Prof.`, `د.`, `أ.د.` …), extra spaces and letter case.
   The same person gets the same code in every form, every round and every run.
3. It writes a copy of every form to `data/processed/pseudonymised/<form type>/`, with each known name
   replaced by its code wherever it appears in the document, including free text such as review
   comments, headers and footers. The document author fields in the Word file properties are cleared too.
4. After writing, it scans every output file for anything that still looks like a name with a title
   (`Dr. …`, `د. …`) and logs a warning with the file name only. Nothing it logs contains a name.

Running it again is safe. Codes already in the mapping are reused and only new people get new codes,
so the output is the same every time (rule 1.2 of the development standards).

## where the mapping lives

The table that links codes back to names is the only file that can undo the pseudonymisation, so:

- It is **never** stored inside the repository. The default location is
  `~/grant-intelligence-private/pseudonym_map.csv` and can be changed with `PSEUDONYM_MAP_PATH` in `.env`.
  The script refuses to write it anywhere inside the repo folder.
- For real data, the Research Unit keeps this file, not the students. We would hand them the script and
  they would run it on their own machine, so we only ever see the pseudonymised copies.
- In production (`APP_ENV=production`), `PSEUDONYM_MAP_PATH` has to be set explicitly, otherwise the
  config raises an error instead of falling back to the default.

## rules for everyone on the team

- Read forms from `data/processed/pseudonymised/`, never from the raw folder, in any analysis code.
- No names in logs, error messages, test output, CSVs, docs or the dashboard. Log file names and grant
  IDs instead.
- Reviewers: analyse in aggregate only. No table, chart or quote should let a reader tell which
  reviewer wrote or scored what. Any reviewer-level figure covers at least 5 reviews or isn't shown, and
  `REVIEWER-##` codes do not appear in any output. They are only there so the code can tell the two
  reviews of one proposal apart.
- Researchers: stall alerts and drift results are about grants, not people. Outputs use the grant ID
  and say "review recommended" or "distance measured", never anything about the researcher.
- `data/raw/*`, `data/processed/*` and `cache/*` are git-ignored (rule 1.9). Before pushing, check
  `git status` for data files that slipped in.

## things that need fixing in the repo

- `data/processed/planned_timetables.csv` and `data/processed/progress_trajectories.csv` are tracked in
  git even though `.gitignore` excludes `data/processed/*`; they were force-added. The timetable file has a
  `researcher` column with names in it. With synthetic data that's harmless, but with real data it would
  be a leak. It should be regenerated from the pseudonymised proposals and removed from git
  (`git rm --cached`). It also stays in the git history, which is exactly what rule 1.9 warns about.
- `inspect_proposals.py`, `ingestion/data_inventory.py` and `app/progress/progress_trajectories.py`
  still default to `data/synthetic/raw`. They should point at the pseudonymised folder.

## known limitations

- An Arabic form and an English form of the same person get two different codes, because we don't
  transliterate (أحمد vs Ahmed). In the synthetic data every grant uses one language, so this doesn't come
  up, but it would split people in real data.
- Two different people with exactly the same name get the same code. A typo or a different spelling of
  the same name gives two codes.
- Only names in the labelled fields are collected. A name that only appears in free text (for example
  a reviewer mentioning a colleague who is on no form) is not replaced. The leftover check catches the
  ones written with a title.
- Names inside images, embedded objects or attached PDFs are not handled.

## how to run it

0. Install the requirements (`pip install -r requirements.txt`) and run from the repository root.
   Check: `python -c "import docx"` prints nothing.
1. Optionally set `PSEUDONYM_MAP_PATH` in `.env` to a folder outside the repo.
2. Run `python -m app.ingestion.pseudonymiser`.
   Check: the last log line reports how many files were written and how many researchers and reviewers
   were found (765 files, 0 leftover warnings on the synthetic data), and
   `data/processed/pseudonymised/` now has five subfolders.
3. Run it a second time.
   Check: it reports 0 new people, and the mapping file is unchanged.
