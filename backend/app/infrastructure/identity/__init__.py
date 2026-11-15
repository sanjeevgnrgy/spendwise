"""The sign-in adapters (infrastructure): standard OpenID Connect, and the one used when sign-in isn't configured.

Only the composition root (bootstrap.py) builds them, from the OIDC_* settings, and hands them to the accounts module
as the IdentityProvider port (core/identity.py). Inside: oidc.py (the provider), documents.py (discovery and keys),
exchange.py (token and UserInfo endpoints), tokens.py (checking tokens), options.py (the login options' setting).
"""

from app.infrastructure.identity.exchange import ClientCredentials
from app.infrastructure.identity.oidc import OidcIdentityProvider
from app.infrastructure.identity.options import OidcLoginOption
from app.infrastructure.identity.unconfigured import UnconfiguredIdentityProvider

__all__ = ["ClientCredentials", "OidcIdentityProvider", "OidcLoginOption", "UnconfiguredIdentityProvider"]
