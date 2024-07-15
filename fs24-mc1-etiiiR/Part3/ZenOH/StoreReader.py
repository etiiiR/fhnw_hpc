import zenoh

config = {
    "connect": {
        "endpoints": ["tcp/localhost:7447"]
    }
}

if __name__ == "__main__":
    session = zenoh.open(config)
    replies = session.get('bus/Bus1/**', zenoh.ListCollector())
    for reply in replies():
        try:
            print("Received ('{}': '{}')"
                .format(reply.ok.key_expr, reply.ok.payload.decode("utf-8")))
        except:
            print("Received (ERROR: '{}')"
                .format(reply.err.payload.decode("utf-8")))
session.close()