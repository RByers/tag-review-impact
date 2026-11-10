# tag-review-impact

A dashboard estimating the impact of [W3C TAG design reviews](https://github.com/w3ctag/design-reviews/issues)
on web platform features: how long reviews take (net of time waiting on the requesters), whether and how
they changed the feature, and which Chrome features and blink-dev Intent to Ship threads they belong to.

- [docs/findings.md](docs/findings.md): initial results.
- [docs/design.md](docs/design.md): pipeline, modules, how to run it.
- [docs/latency.md](docs/latency.md): the latency model and results.
- [docs/taxonomy.md](docs/taxonomy.md): the impact labels, how they were chosen, and the audit.
- [docs/chromestatus.md](docs/chromestatus.md): linking reviews to chromestatus features and blink-dev.
- [SECURITY.md](SECURITY.md): GitHub threads are untrusted; how models read them safely.

```sh
cd web && npm install && npm run serve    # http://localhost:5184
```
