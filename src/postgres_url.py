"""Build SQLAlchemy PostgreSQL URLs with correctly encoded credentials."""
from urllib.parse import quote_plus


def build_postgres_sqlalchemy_url(
    user: str,
    password: str,
    host: str,
    port: str,
    dbname: str,
) -> str:
    """
    Return a postgresql:// URL safe for passwords containing @, :, /, etc.

    Unquoted @ in the password is parsed as the end of userinfo, which breaks
    the hostname (e.g. password ``x@y`` yields host ``y@localhost``).
    """
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{dbname}"
    )
