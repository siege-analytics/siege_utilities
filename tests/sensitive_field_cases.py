"""Export and marker-guard cases, independent of the production classifier."""

SECRET_NAMES = (
    "webhook_secret", "bot_token", "signing_key", "api_keys",
    "connection_string", "connectionString", "passphrase", "apikey", "apiKey",
    "privateKey", "passwd", "pwd", "dsn", "secret", "token", "password",
    "api_key", "private_key", "connection", "privatekey", "connectionstring",
    "api-key", "private-key", "ssh-key", "access-key", "x-api-key",
    "accessKey", "accessKeyId", "access_key", "auth", "authorization",
    "auth_header", "basic_auth", "bearer", "jwt", "cookie", "session",
    "session_id", "session_token", "session_cookie", "credential", "credentials",
    "pem", "cert", "cert_pem", "key_pem", "signing_pem", "key",
    "api.key", "private key", "Authorization", "ACCESS_KEY_ID", "SSHKey",
    "public_key_secret", "token_count_password",
    "apiKey2", "password2", "db_password1", "apikeys", "secrets", "passwords",
    "clientsecret", "accesstoken", "refreshtoken", "secretkey", "accesskey", "sessionid",
)

PUBLIC_NAMES = (
    "token_count", "max_tokens", "tokenizer", "password_policy",
    "password_min_length", "primary_key", "foreign_key", "secretary", "dsn_count",
    "public_key", "partition_key", "sort_key", "cache_key", "idempotency_key",
    "token_type", "keyboard", "monkey", "keys_count", "api_version",
    "token_version", "password_length", "min_tokens", "primaryKey", "public-key",
    "token.count", "password policy",
    "author", "turkey", "hockey",
)
