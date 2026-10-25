# bridge — pont avec l'application pédagogique (ISI)

Signed endpoints under `/internal/sync/` (disabled = 404 while `SYNC_SHARED_SECRET` is empty):
* `POST formations/` — ISI pushes a formation -> `Offering` (+ auto fiche technique), idempotent.
* `GET feed/?cursor=N` — clients changed since event N (full current snapshot each);
  `?mode=head` current cursor; `?mode=full&after_id=N` every client (repair/backfill).

Changes are recorded by `signals.py` (one `SyncEvent` row per client, re-created on each change).
Code paths that use `queryset.update()` must call `bridge.signals.record_clients_changed(ids)`
(audited: only the two EnrollmentAdmin actions needed it); ISI also re-walks known clients daily.
Staff are emailed (ADMINS / support@) when ISI creates an offering or hides one; Admin > Offerings has an "ISI sync" filter for offerings awaiting review.
New offerings are created hidden (`SYNC_NEW_OFFERINGS_ACTIVE=0`); publish from Admin > Liens formations ISI.
`POST formations/deactivate/` hides offerings of formations deleted in ISI.
`FormationLink` ties an ISI formation to its Offering and remembers the last values synced, so
website-side edits are never overwritten. See `isi.../sync/README.md` for setup.
