# amazon-feed
A simple Python script to generate a [JSON Feed](https://github.com/brentsimmons/JSONFeed) for search results on [Amazon](https://www.amazon.com).

Uses the unofficial API and served over [Flask!](https://github.com/pallets/flask/)

Use the [Docker build](https://hub.docker.com/r/leonghui/amazon-feed) to host your own instance.

1. Set your timezone as an environment variable (see [docker docs]): `TZ=America/Los_Angeles`

2. Access the feed using the URL: `http://<host>/?query={query_string}`

3. Optionally, filter by:
    - country: `http://<host>/?query={query_string}&country={AU/BR/CA/CN/FR/DE/IN/IT/JP/MX/NL/ES/TR/AE/UK/US}`
    - max price: `http://<host>/?query={query_string}&max_price={int}`
    - min price: `http://<host>/?query={query_string}&min_price={int}`
    - srp only: `http://<host>/?query={query_string}&srp_only=yes`
    - strict mode (terms must appear in the title): `http://<host>/?query={query_string}&strict=yes`

E.g.
```
Search results for "radeon 6800" on Amazon.sg between $800 to $1250:
https://www.amazon.sg/s?k=6800+amd&rh=p_36%3A80000-125000

Feed link:
http://<host>/?query=radeon%206800

Filtered feed link:
http://<host>/?query=radeon%206800&min_price=800&max_price=1250&country=sg&srp_only=true&strict=true
```

Tested with:
- [Nextcloud News App](https://github.com/nextcloud/news)

[docker docs]:(https://docs.docker.com/compose/environment-variables/#set-environment-variables-in-containers)