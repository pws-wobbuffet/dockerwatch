# TODO.md

## DockerWatch — Task List

### Phase 1 — Project scaffold
- [x] 1. Create repo, init git, write DECISIONS.md / ARCHITECTURE.md / TODO.md
- [x] 2. Commit architecture docs

### Phase 2 — Core backend
- [x] 3. Write `requirements.txt`
- [x] 4. Write `src/models.py` (Pydantic response models)
- [x] 5. Write `src/docker_client.py` (Docker SDK wrapper)
- [x] 6. Write `src/main.py` (FastAPI routes)
- [x] 7. Write `Dockerfile` and `.env.example`
- [x] 8. Write `docker-compose.yml`
- [x] 9. Smoke-test: `docker compose up --build` — verify API responds

### Phase 3 — Frontend
- [x] 10. Write `src/static/index.html` (dashboard shell + CSS)
- [x] 11. Add polling loop and container card rendering
- [x] 12. Add log viewer modal
- [x] 13. Add start/stop actions with confirmation
- [x] 14. End-to-end manual test

### Phase 4 — Docs and quality gate
- [x] 15. Write `README.md`
- [x] 16. Run full quality gate checklist
- [x] 17. Fix any issues found

### Phase 5 — Publish
- [x] 18. `gh repo create` + push
- [x] 19. `gh release create v0.1.0`
- [x] 20. Print repo URL

### Deferred (out of scope for MVP)
- Historical metrics persistence (SQLite time-series) — would require schema + migration
- Container resource limit editing — requires privileged Docker API calls
- Multi-host support — requires remote Docker daemon config
