# Phase 10 — Task Checklist

Tracker for `TODO_phase10_SPEC.md`. One task at a time, in order — 10.0 is a hard
dependency for everything else. Check a box only once its tests pass against the
real codebase (not the spec's ASSUME placeholders).

- [x] **10.0** Foundational data model changes: `EnrollmentParticipant` model,
  `Enrollment.roster_locked_at`, `EnrollmentNote.visible_to_client`, one migration
  covering all three, `EnrollmentParticipant` registered in admin, `visible_to_client`
  added to `EnrollmentNoteInline`.
- [x] **10.1** Email on enrollment acceptance (pre_save/post_save signal pair +
  `enrollment/services.py::notify_enrollment_accepted` + `emails/enrollment_accepted.html`).
  Also fixed `EnrollmentAdmin.mark_accepted` to save per-object instead of
  `queryset.update()`, since the latter bypasses signals entirely.
- [x] **10.2** Company roster: `EnrollmentParticipant` CRUD view (dynamic formset,
  no reload per row), seat-cap enforcement, staff read-only entry points, CSV export.
- [x] **10.3** Quick-register CTA with prefill for authenticated/active clients.
- [x] **10.4** Fix: accepted enrollment not reflected in `/mon-espace/` dashboard.
- [x] **10.5** Surface staff notes to the client (depends on 10.0.3).
- [x] **10.6** Login redirect to `/mon-espace/` + catalogue quick-access.
- [x] **10.7** Schedule the session with a specific date (locks roster, emails
  client, generates session-brief bridge artifact for the pedagogical app hand-off).
