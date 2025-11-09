# amazon-feed
A simple Python script to generate a [JSON Feed](https://www.jsonfeed.org/) for search results on [Amazon](https://www.amazon.com).

Uses [BeautifulSoup 4](https://www.crummy.com/software/BeautifulSoup/) and served over [FastAPI!](https://fastapi.tiangolo.com/)

Use the [Docker build](https://github.com/users/leonghui/packages/container/package/amazon-feed) to host your own instance.

1. Set your timezone as an environment variable (see [docker docs]): `TZ=America/Los_Angeles`

2. Access the feed using the URL: `http://<host>/?q={query_string}`

3. Optionally, filter by:
    - country: `http://<host>/?q={query_string}&country={AU/DE/ES/FR/IT/SG/UK/US}`
    - max price: `http://<host>/?q={query_string}&max_price={int}`
    - min price: `http://<host>/?q={query_string}&min_price={int}`
    - strict mode (terms must appear in the title): `http://<host>/?q={query_string}&strict=yes`

E.g.
```
Search results for "radeon 6800" on Amazon.sg between $800 to $1250:
https://www.amazon.sg/s?k=6800+amd&rh=p_36%3A80000-125000

Feed link:
http://<host>/?q=radeon%206800

Filtered feed link:
http://<host>/?q=radeon%206800&min_price=800&max_price=1250&country=sg&strict=true
```

API docs:
http://localhost:8000/docs

Tested with:
- [Nextcloud News App](https://github.com/nextcloud/news)

[docker docs]:(https://docs.docker.com/compose/how-tos/environment-variables/#set-environment-variables-in-containers)
