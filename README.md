# 4NextDart

Alexa skill that tells you when the next Dublin DART trains are due at a station, using the
NTA GTFS-Realtime API. Sibling of [4NextBus](https://github.com/ZarleyLtd/4NextBus) and
[4NextTram](https://github.com/ZarleyLtd/4NextTram).
Store name: **4NextDart**. Invocation: **four next dart**.

- "Alexa, ask four next dart from Pearse southbound"
- "Alexa, ask four next dart from Blackrock towards the city"
- "Alexa, ask four next dart to set my favourite stop to Bray northbound"
- "Alexa, ask four next dart for my favourite stop"
- "Alexa, ask four next dart" (uses your favourite)

Only **DART** trains are included, even at stations that also have Commuter or Intercity
services. A favourite is **one direction at a named station** (GTFS uses one stop id per
station; northbound and southbound are split by destination).

## You do this

The code and AWS scripts live in this repo. These steps need you (Amazon console, GitHub
Pages, secrets). Do not reuse the 4NextBus or 4NextTram skill IDs.

### Before deploy

1. **Amazon Developer Console** — Create a custom skill named `4NextDart`, locale **en-GB**,
   invocation **four next dart**. Copy the skill ID (`amzn1.ask.skill....`).
2. Check on amazon.co.uk that nothing already intercepts "four next dart".
3. Reuse the existing AWS account (`eu-west-1`) and the same NTA GTFS-R key as bus/tram.
4. GitHub repo is already [ZarleyLtd/4NextDart](https://github.com/ZarleyLtd/4NextDart).
5. Optional: drop `4NextDartIcon.jpg` in the project root, then run
   `python tools/make_skill_icons.py`. A placeholder icon is generated if the jpg is missing.

### After the Lambda exists

6. Copy `.env.example` to `.env`. Set `ALEXA_SKILL_ID`, `ALERT_EMAIL`, `NTA_API_KEY`.
7. `python tools/deploy.py all` — creates stack `FourNextDart`, Lambda `FourNextDart-Skill`,
   SSM `/4nextdart/nta_api_key`. It prints the Lambda ARN.
8. First timetable: `python -m ingest.build_timetable`.
9. Alexa console:
   - Build → JSON Editor: paste `skill-package/interactionModels/custom/en-GB.json` → Save & Build.
   - Endpoint: `eu-west-1`, paste the Lambda ARN.
   - Distribution: upload `skill-package/assets/images/en-GB_smallIcon.png` (108×108) and
     `en-GB_largeIcon.png` (512×512). Privacy:
     https://zarleyltd.github.io/4NextDart/privacy.html
10. **GitHub Pages** on this repo from `/docs` so the privacy page and icons are live.
11. `python tools/deploy.py ingest-key` → GitHub secrets `AWS_ACCESS_KEY_ID` /
    `AWS_SECRET_ACCESS_KEY` (optional vars `AWS_REGION`, `FOURNEXTDART_TABLE`).
12. Console Test tab / a device: Pearse southbound, set favourite, launch with no slots,
    Howth Junction, Help/Stop.
13. Publish when you want it in the store.

Smoke test: `python tools/deploy.py test --station Pearse --direction southbound`.

Later code changes: `python tools/deploy.py code`.

## Layout

```
src/common/        GTFS time handling, predictions, realtime fetch, speech, DynamoDB, station matching
src/skill/         Lambda handler (ask-sdk-core)
ingest/            daily timetable build (DuckDB over the TFI GTFS zip -> DynamoDB)
tools/             local proof-of-concept and helper scripts
skill-package/     Alexa skill manifest and en-GB interaction model
tests/             pytest
template.yaml      CloudFormation: DynamoDB table, Lambda, role, SSM parameter
```

## Voice model

Canonical files:

- Interaction model: [`skill-package/interactionModels/custom/en-GB.json`](skill-package/interactionModels/custom/en-GB.json)
- Store listing: [`skill-package/skill.json`](skill-package/skill.json)
- Regenerate the model from GTFS: `python tools/build_voice_model.py`

Paste the JSON into the Alexa console **Build → Interaction Model → JSON Editor**, then Save
and Build. A new unpublished skill can start with `en-GB` only.

### Invocation vs display name

| What users see / say | Value |
| --- | --- |
| Skill name (store and console) | `4NextDart` |
| Invocation name (spoken) | `four next dart` |

### Custom intents

| Intent | Slots | Purpose |
| --- | --- | --- |
| `NextDartIntent` | `station` (`DART_STATION`), optional `direction` (`DART_DIRECTION`) | Times at a station, or at the favourite |
| `SetFavouriteStopIntent` | same | Save one favourite direction at a station |
| `GetFavouriteStopIntent` | none | Read back the favourite |

Direction phrases, where they apply at that station:

- Cardinal: northbound / southbound
- City: towards the city (suburban stations only; Connolly, Tara Street, and Pearse elicit a terminus)
- Terminus: towards Howth, Malahide, Bray, or Greystones

Howth Junction northbound covers both Howth and Malahide; you can also say towards Howth or towards Malahide.

Dialog is `SKILL_RESPONSE`: Lambda elicits `station` or `direction` when needed.

## Data sources

- Realtime: `https://api.nationaltransport.ie/gtfsr/v2/TripUpdates` (header `x-api-key`), max 1 call / 60 s **per key**.
- Static timetable: `https://www.transportforireland.ie/transitData/Data/GTFS_Realtime.zip`, **route_type 2** and **route_short_name DART**.
  Do not ingest standalone `GTFS_Irish_Rail.zip` for production IDs — they must match GTFS-R v2.

## Local setup (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
copy .env.example .env   # then fill in NTA_API_KEY
.\.venv\Scripts\python tools\poc_next_dart.py Pearse --direction southbound --no-realtime
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python tools\build_voice_model.py
```

If `pip` fails with `CERTIFICATE_VERIFY_FAILED`, bootstrap once with
`--trusted-host pypi.org --trusted-host files.pythonhosted.org --upgrade pip truststore`.

NTA only issues one GTFS-Realtime subscription per developer account. 4NextDart
shares that key with live 4NextBus and 4NextTram. Before calling NTA it claims the
same DynamoDB lock item as the bus skill (`FourNextBus` `META/RTLOCK`), so the
combined skills stay at one TripUpdates call per 60 seconds. The loser uses a
cached feed if that Lambda container has one, otherwise timetable times (“scheduled”).
Set `NTA_LOCK_TABLE` if the bus table name is not `FourNextBus`.

Daily ingest in `.github/workflows/ingest.yml` runs at **00:25 UTC** (after 4NextBus
at 00:10). GitHub’s public `schedule` queue is often 6–7 hours late, so an overnight
cron still usually finishes before the Irish morning peak; 04:10 UTC was landing
around midday.

## Free tier

Same shape as 4NextBus: Lambda, one provisioned DynamoDB table, CloudWatch Logs, SSM Parameter Store,
GitHub Actions for the daily timetable build.
