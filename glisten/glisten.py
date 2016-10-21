#!/usr/bin/env python3.5
#
# Parts of this file
# Copyright (c) 2016 by Ron Frederick <ronf@timeheart.net>.
# All rights reserved.
#
# This program and the accompanying materials are made available under
# the terms of the Eclipse Public License v1.0 which accompanies this
# distribution and is available at:
#
#     http://www.eclipse.org/legal/epl-v10.html
#
# Contributors:
#     Ron Frederick - initial implementation, API, and documentation

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

async def get_name_handler(request):
    name = request.app['latest_project_name']
    text = "The name is: " + name
    return web.Response(text=text)

async def post_handler(request):

    # WARNING: don't do this if you plan to receive large files!
    project_name = await request.json()

    request.app['latest_project_name'] = project_name['project_name']

    text = "Data Recieved!"

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

class StreamEventsSession(asyncssh.SSHServerSession):
    _clients = []

    def __init__(self, stdin, stdout, stderr):
        self._stdin = stdin
        self._stdout = stdout

    @classmethod
    async def handle_session(cls, stdin, stdout, stderr):
        await cls(stdin, stdout).run()

    def write(self, msg):
        self._stdout.write(msg)

    def broadcast(self, msg):
        for client in self._clients:
            if client != self:
                client.write(msg)

    async def run(self):
        self.write('Welcome to chat!\n\n')

        self.write('Enter your name: ')
        name = (await self._stdin.readline()).rstrip('\n')

        self.write('\n%d other users are connected.\n\n' % len(self._clients))

        self._clients.append(self)
        self.broadcast('*** %s has entered chat ***\n' % name)

        try:
            async for line in self._stdin:
                self.broadcast('%s: %s' % (name, line))
        except asyncssh.BreakReceived:
            pass

        self.broadcast('*** %s has left chat ***\n' % name)
        self._clients.remove(self)


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

    def session_requested(self):
        return StreamEventsSession

def create_handler(data_holder):
    def handle_session_modified(stdin, stdout, stderr):
        stdout.write('Welcome to my SSH server, %s!\n' % 
                      data_holder['latest_project_name'])
        stdout.channel.exit(0)
    return handle_session_modified



async def start_server(data_holder):
    handler  = create_handler(data_holder)
    await asyncssh.create_server(MySSHServer, '', 8022,
                                 server_host_keys=['ssh_host_key'],
                                 session_factory=handler
                                 )

class Glisten():
    def __init__(self):
        self.latest_project_name = 'initial_name'
        self.data_holder = { 'latest_project_name': self.latest_project_name }

        # SSH server
        self.loop = asyncio.get_event_loop()
        ssh_server = start_server(self.data_holder)
        self.loop.run_until_complete(ssh_server)

        # http server
        app = web.Application()
        app.router.add_get('/echo', wshandler)
        app.router.add_get('/', handle)
        app.router.add_get('/get_name', get_name_handler)
        app.router.add_post('/post', post_handler)
        app['latest_project_name'] = self.latest_project_name

        # this calls run_until_complete somewhere
        web.run_app(app)


if __name__ == "__main__":

    glisten = Glisten()


