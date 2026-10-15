"""TLS tweak: announce the prime256v1 curve (the one a regular browser uses).

Some video stream servers (Vidzy's CDN, vidzy.cc) answer `403` to connections whose
TLS fingerprint is Python/OpenSSL's default, while a browser or curl gets through.
It is neither the Referer nor the User-Agent: it is the list of curves offered when
the connection opens. Announcing prime256v1 makes the same request receive `200`.
No site is penalized by this choice: P-256 is accepted everywhere.

Call apply() once (idempotent) before making requests.
"""

_CURVE = "prime256v1"
_done = False


def apply():
    global _done
    if _done:
        return
    _done = True
    try:
        import requests.adapters as _adapters
        ctx = getattr(_adapters, "_preloaded_ssl_context", None)
        if ctx is not None:
            ctx.set_ecdh_curve(_CURVE)

        import urllib3.util.ssl_ as _ssl_util
        original = _ssl_util.create_urllib3_context

        def create_urllib3_context(*args, **kwargs):
            context = original(*args, **kwargs)
            try:
                context.set_ecdh_curve(_CURVE)
            except Exception:
                pass
            return context

        _ssl_util.create_urllib3_context = create_urllib3_context
        try:
            import urllib3.connection as _connection
            if hasattr(_connection, "create_urllib3_context"):
                _connection.create_urllib3_context = create_urllib3_context
        except Exception:
            pass
    except Exception:
        # a comfort tweak: never prevent the program from starting
        pass
