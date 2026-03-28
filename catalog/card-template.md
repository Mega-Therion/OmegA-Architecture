# Card Template

Use this template for any new catalog card or registry entry.

## Required Fields

- `name`
- `path`
- `category`
- `purpose`
- `owner`
- `read_first`
- `allowed_contents`
- `forbidden_contents`
- `validation`

## Card Rules

- Keep the card to one artifact family.
- Describe the canonical home, not the historical path list.
- Include the first document or tool a new agent should read.
- State the validation command or gate that protects the folder.

## Example

- `name`: `evals`
- `path`: `./evals`
- `category`: `validation`
- `purpose`: regression suites and evidence outputs
- `owner`: `architecture/runtime`
- `read_first`: `catalog/INDEX.md`
- `allowed_contents`: harnesses, results, baselines, evidence indexes
- `forbidden_contents`: product source, secrets, unrelated docs
- `validation`: `python3 scripts/catalog_guard.py`
