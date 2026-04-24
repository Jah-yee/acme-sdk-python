# Authentication

The Acme SDK supports two authentication methods: API Key and OAuth 2.0.

## API Key Authentication

The simplest authentication method using a static API key.

```python
from acme_sdk import AcmeClient

client = AcmeClient(api_key="your-api-key")
```

Obtain your API key from the [Acme dashboard](https://app.acme-sdk.dev/api-keys).

## OAuth 2.0 Authentication

For applications that need to act on behalf of users, the SDK supports OAuth 2.0 Client Credentials flow.

### Setup

```python
from acme_sdk import AcmeClient
from acme_sdk.auth import OAuthProvider

auth = OAuthProvider(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://auth.acme-sdk.dev/oauth/token",
)

client = AcmeClient(auth_provider=auth)
```

### Scopes

The SDK requests the following scopes by default: `traces:write`, `metrics:write`, `events:write`.

To request custom scopes, pass a `scopes` list:

```python
auth = OAuthProvider(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://auth.acme-sdk.dev/oauth/token",
    scopes=["traces:write", "metrics:write"],
)

client = AcmeClient(auth_provider=auth)
```

### Token Refresh

The OAuthProvider automatically refreshes expired tokens. Tokens are refreshed in the background before they expire.

### Revoking Tokens

To explicitly revoke the current access token:

```python
auth = client.auth_provider
auth.revoke()
```

### Validating Credentials

To check if the credentials are valid without making an API call:

```python
from acme_sdk.auth import OAuthProvider

auth = OAuthProvider(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://auth.acme-sdk.dev/oauth/token",
)

if auth.is_valid():
    print("Credentials are valid")
else:
    print("Credentials are invalid or expired")
```

### Cleanup

When done, close the auth provider to release resources:

```python
auth.close()
```

## Choosing an Authentication Method

| Method | Use Case |
|--------|----------|
| API Key | Server-to-server communication, simple integrations |
| OAuth 2.0 | Multi-tenant applications, user-delegated access |

## Environment Variables

You can also configure authentication via environment variables:

```bash
export ACME_API_KEY="your-api-key"
```

Or in a config file:

```toml
[acme]
api_key = "${ACME_API_KEY}"
```
