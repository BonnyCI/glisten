from aiohttp import web
import asyncio, asyncssh, crypt, sys

# To run this program, the file ``ssh_host_key`` must exist with an SSH
# private key in it to use as a server host key. An SSH host certificate
# can optionally be provided in the file ``ssh_host_key-cert.pub``.
passwords = {'guest': '',                 # guest account with no password
             'user123': 'qV2iEadIGV2rw'   # password of 'secretpw'
            }

async def handle(request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)

async def wshandler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == web.MsgType.text:
            ws.send_str("Hello, {}".format(msg.data))
        elif msg.type == web.MsgType.binary:
            ws.send_bytes(msg.data)
        elif msg.type == web.MsgType.close:
            break

    return ws

def handle_session(stdin, stdout, stderr):
    stdout.write('Welcome to my SSH server, %s!\n' %
                 stdout.channel.get_extra_info('username'))
    stdout.channel.exit(0)

class MySSHServer(asyncssh.SSHServer):
    def connection_made(self, conn):
        print('SSH connection received from %s.' %
                  conn.get_extra_info('peername')[0])

    def connection_lost(self, exc):
        if exc:
            print('SSH connection error: ' + str(exc), file=sys.stderr)
        else:
            print('SSH connection closed.')

    def begin_auth(self, username):
        # If the user's password is the empty string, no auth is required
        return passwords.get(username) != ''

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        pw = passwords.get(username, '*')
        return crypt.crypt(password, pw) == pw

async def start_server():
    await asyncssh.create_server(MySSHServer, '', 8022,
                                 server_host_keys=['ssh_host_key'],
                                 session_factory=handle_session)

loop = asyncio.get_event_loop()
loop.run_until_complete(start_server())

app = web.Application()
app.router.add_get('/echo', wshandler)
app.router.add_get('/', handle)
app.router.add_get('/{name}', handle)

web.run_app(app)