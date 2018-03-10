import argparse
import asyncio
import json
import time

# from quarkchain.local import LocalClient
from quarkchain.protocol import Connection, ConnectionState
from quarkchain.local import OP_SER_MAP, LocalCommandOp, JsonRpcRequest
from quarkchain.config import DEFAULT_ENV


class LocalClient(Connection):

    def __init__(self, loop, env, reader, writer):
        super().__init__(env, reader, writer, OP_SER_MAP, dict(), dict(), loop=loop)
        self.loop = loop
        self.miningBlock = None
        self.isMiningBlockRoot = None

    async def start(self):
        self.state = ConnectionState.ACTIVE
        asyncio.ensure_future(self.activeAndLoopForever())

    async def callJrpc(self, method, params=None):
        jrpcRequest = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            jrpcRequest["params"] = params

        op, resp, rpcId = await self.writeRpcRequest(
            LocalCommandOp.JSON_RPC_REQUEST,
            JsonRpcRequest(json.dumps(jrpcRequest).encode()))
        return json.loads(resp.jrpcResponse.decode())

    def closeWithError(self, error):
        print("Closing with error {}".format(error))
        return super().closeWithError(error)

    @staticmethod
    def callJrpcSync(host, port, method, **kwargs):
        loop = asyncio.new_event_loop()
        coro = asyncio.open_connection(host, port, loop=loop)
        reader, writer = loop.run_until_complete(coro)
        client = LocalClient(loop, DEFAULT_ENV, reader, writer)
        loop.create_task(client.start())
        jrpcResp = loop.run_until_complete(client.callJrpc(method, params=kwargs))
        client.close()
        loop.run_until_complete(client.waitUntilClosed())
        loop.close()
        return jrpcResp


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--local_port", default=DEFAULT_ENV.config.LOCAL_SERVER_PORT, type=int)
    parser.add_argument(
        "--method", default=None, type=str)
    parser.add_argument("--times", default=1, type=int)
    parser.add_argument("--interval", default=2.0, type=float)
    parser.add_argument("--params", default=None, type=str)
    args = parser.parse_args()

    if args.method is None:
        raise RuntimeError("method must be specified")
    return args


def main():
    args = parse_args()
    params = None
    if args.params is not None:
        params = json.loads(args.params)
    loop = asyncio.get_event_loop()
    coro = asyncio.open_connection("127.0.0.1", args.local_port, loop=loop)
    reader, writer = loop.run_until_complete(coro)
    client = LocalClient(loop, DEFAULT_ENV, reader, writer)
    asyncio.ensure_future(client.start())
    for i in range(args.times):
        jrpcResp = loop.run_until_complete(client.callJrpc(args.method, params=params))
        print(json.dumps(jrpcResp, sort_keys=True, indent=4))
        if i != args.times - 1:
            time.sleep(args.interval)

    client.close()
    loop.run_until_complete(client.waitUntilClosed())
    loop.close()


if __name__ == '__main__':
    main()