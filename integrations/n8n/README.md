# n8n workflows

- `workflows/craigslist_48h_bump_reminder.json`: the Telegram reminder to renew the Craigslist
  listings. Imported by hand; see `docs/runbooks/kubelab-integration.md`, section 2.
- **The daily sale-metrics digest is not here.** The kubelab repository owns it and imports it as
  code (kubelab#2088, kubelab#2090):
  `infra/n8n/workflows/sale-metrics-daily-digest.json` in `mlorentedev/kubelab`. A second copy in
  this repository would drift from the one that runs, so there is none.
  `docs/runbooks/kubelab-integration.md`, section 3, has the owner steps, and ADR-011 records the
  decision.

What this repository still owes the digest is the data it reads. The digest queries the Workers
Analytics Engine dataset `leaving_denver_sale_events` (named in `wrangler.toml`) for the columns
`blob1` event, `blob2` source, `blob3` item, `blob4` bundle and `SUM(_sample_interval)`, which is
the data point `functions/api/hit.js` writes. Change that shape, the dataset name or a source name
and the kubelab workflow must change with it; `tests/test_sale_metrics_workflow.py` checks the two
against each other when it is pointed at the kubelab file.
