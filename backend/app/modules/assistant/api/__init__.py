"""The assistant's adapters: the outside world in and out (HTTP, and AG-UI over Server-Sent Events).

Adapter layer, with no rules of its own: routes.py (POST /parse, /chat, /agent), schemas.py (their request and
response bodies), agui_request.py (AG-UI in: a run, checked), agui_stream.py (AG-UI out: the events) and
protocol.py (names on the wire beyond AG-UI's own). They translate HTTP into the use cases (application/);
module.py builds the router from routes.py. Nothing is exported here: each file is imported by its full path.
"""
