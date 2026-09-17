# Gomaa Intelligence — Autonomous Lead Radar

GitHub Actions-ready discovery, lead normalization, service matching, reporting, and gated outreach automation for Gomaa Intelligence.

## What is automated

- Discovers businesses from configured public business directories; no manual company URL list is required.
- Processes 22 Arab/MENA countries and a broad sector map.
- Crawls only publicly accessible pages and respects robots.txt plus HTTP access signals.
- Extracts multiple business records from directory cards / structured data instead of treating an entire directory page as one company.
- Extracts public company names, websites, emails, phones, and social links.
- Normalizes and deduplicates emails and filters obvious system addresses.
- Scores contact roles such as sales, business, marketing, owner, manager, contact, info, and support.
- Maps sectors to relevant Gomaa Intelligence services and personalizes the company name in the message.
- Keeps discovery tasks, send history, suppression records, permissions, and campaign state in SQLite.
- Produces CSV/JSON reports as GitHub Actions artifacts.

## Sending safety / provider gate

The project is intentionally configured with `send_policy: permissioned`.
A public email discovered by scraping is **not** treated as permission to send.
For Resend specifically, its current Acceptable Use Policy prohibits unsolicited cold outreach, purchased lists, and scraped contact data, and requires explicit opt-in for mailing lists. See the current Resend policy before enabling any live campaign.

The code therefore supports automatic sending only for contacts that are actually recorded as opted-in in the `permissions` table. This is a provider/compliance gate, not a manual per-message workflow.

Do not use the project to bypass CAPTCHAs, WAFs, authentication, robots restrictions, rate limits, or provider restrictions.

## Daily campaign behavior

- Hard daily cap: 40 successful sends.
- Delay: 180 seconds between live sends.
- The cap is checked against the database by calendar day, so repeatedly starting the workflow cannot silently exceed 40 successful sends for that day.
- A stable per-recipient/day idempotency key is used for provider retries.
- Discovery, campaign, and maintenance workflows share one serialized database concurrency group.
- Scheduled campaign runs execute the live campaign command; manual runs default to dry-run.
- Failed provider calls return the lead to `new` and record a failure event.
- A maintenance workflow recovers stale `sending` rows after runner interruption.

## GitHub Actions secrets

Required for live Resend sending:

- `RESEND_API_KEY`
- `FROM_EMAIL`
- `REPLY_TO_EMAIL`

The project is prepared for:

`REPLY_TO_EMAIL=ahmedgomaelsayed@gmail.com`

Do not commit API keys or other secrets to the repository.

## Workflows

- `discovery.yml` — scheduled every 6 hours and manually runnable.
- `campaign.yml` — scheduled daily and manually runnable with dry-run/live choice.
- `maintenance.yml` — daily database recovery/report job.

The SQLite database is persisted between GitHub Actions runs through the Actions cache. All three workflows use the same concurrency group so they do not operate on the database simultaneously.

## Local checks

```bash
python -m app init-db
python -m app discover
python -m app report
python -m app campaign --dry-run --limit 40
python -m app maintenance
pytest -q
```

## Scope

The engine does not require a user-provided company list. It discovers from the public sources defined in `config/sources.yml` and can be extended with additional public sources without changing the campaign core.
