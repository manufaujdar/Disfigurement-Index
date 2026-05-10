# Disfigurement Index Website Prototype

Doctor-only Disfigurement Index website prototype with:

- Backend JSON API.
- SQLite database.
- Calculation engine.
- Calculator and saved assessment records.
- Database-backed doctors forum.
- Clinical guide with evidence references, author page, doctors forum, and data-governance page.

## Run Locally

```bash
python3 server.py 4173
```

Open:

```text
http://127.0.0.1:4173
```

The local SQLite database is created automatically at:

```text
data/disfigurement_index.sqlite3
```

The `data/` directory is ignored by Git.

## Pages

- `index.html` - backend-powered calculator and recent saved calculations.
- `about.html` - clinical-use guide.
- `forum.html` - doctors feedback forum stored in SQLite.
- `author.html` - author and contributor details.
- `privacy.html` - data governance and prototype privacy boundaries.

## API

- `GET /api/health`
- `GET /api/config`
- `POST /api/calculate`
- `POST /api/assessments`
- `GET /api/forum`
- `POST /api/forum`

## Medical Safety Note

The current algorithm is a research-informed development scaffold, not the final validated Disfigurement Index formula. It uses constructs from established scar and appearance assessment instruments so the website can be tested end-to-end. Replace it with the completed research protocol, validated weights, score bands, missing-data rules, and reference test cases before any clinical, medico-legal, or regulatory use.

## Test

```bash
python3 -m unittest discover -s tests
```
