# Dated Web Change Evidence

A small Python standard library sample that records visible HTML text, a UTC check time, and a SHA256 hash. It can compare a new page snapshot with a prior JSON baseline.

The project is a public technical sample. It is not a claim of client work or measured conversion impact.

For a scoped website evidence and conversion QA review, see Gang Qu's [public service page](https://chris-saas-services.stomeonst123.chatgpt.site) or email [stomeonst123@gmail.com](mailto:stomeonst123@gmail.com). Scope, availability, and a mutually usable payment method are confirmed before any paid work starts.

## Why this exists

Page changes are easy to notice and hard to document consistently. This sample creates a compact evidence record that answers four questions:

1. What source was checked?
2. When was it checked?
3. What visible text was present?
4. Did the normalized visible text change since the baseline?

## Run the deterministic example

Python 3.10 or newer is recommended.

```bash
python3 monitor.py fixtures/before.html --write-baseline evidence.json
python3 monitor.py fixtures/after.html --baseline evidence.json
```

The second command reports `"changed": true` because the visible hero copy and call to action changed.

## Monitor a public page

```bash
python3 monitor.py https://example.com --write-baseline example.json
python3 monitor.py https://example.com --baseline example.json
```

Use URL monitoring only where you have permission. Respect site terms, robots rules, rate limits, privacy obligations, and applicable law. The program performs one request per command and caps the response at 2 MB.

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

## Scope

The sample intentionally omits JavaScript rendering, scheduled execution, selector specific extraction, screenshots, and network retries. Those belong in a production design after the target site and evidence requirements are known.

## Output fields

`checked_at` is a UTC timestamp. `text_sha256` hashes normalized visible text. `previous_hash` records the compared baseline. `changed` is true only when a baseline exists and the hashes differ. `excerpt` provides a short human review cue.

## License

MIT
