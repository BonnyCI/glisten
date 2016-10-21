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
    events = request.app['glisten_events']
    text = "The first event is: " + events.get_first_event()
    return web.Response(text=text)


async def post_handler(request):

    # WARNING: don't do this if you plan to receive large files!
    project_name = await request.json()

    events = request.app['glisten_events']
    events.add_event(project_name['project_name'])

    text = "Data Recieved!"

    return web.Response(text=text)


class StreamEventsSession(asyncssh.SSHServerSession):
    _clients = []

    def __init__(self, stdin, stdout):
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


def create_handler(events, clients):
    async def handle_session_modified(stdin, stdout, stderr):
        while True:
            event = await events.get_last_event()
            stdout.write('Welcome to my SSH server, %s!\n' % event)

    return handle_session_modified


async def start_server(events, clients):
    handler  = create_handler(events, clients)
    await asyncssh.create_server(MySSHServer, '', 8022,
                                 server_host_keys=['ssh_host_key'],
                                 session_factory=)


class Events:
    def __init__(self):
        self.events = []

    def add_event(self, event):
        self.events.append(event)

    def delete_event(self, event):
        self.events.remove(event)

    def get_first_event(self):
        return self.events[0]

    def get_last_event(self):
        event = self.events.pop()
        return event


class Glisten():
    def __init__(self):

        self.events = Events()
        self.clients = []
        self.events.add_event("first event")

        # SSH server
        self.loop = asyncio.get_event_loop()
        ssh_server = start_server(self.events, self.clients)
        self.loop.run_until_complete(ssh_server)

        # http server
        app = web.Application()
        app.router.add_get('/', handle)
        app.router.add_get('/get_name', get_name_handler)
        app.router.add_post('/post', post_handler)
        app['glisten_events'] = self.events

        # this calls run_until_complete somewhere
        web.run_app(app)


if __name__ == "__main__":

    glisten = Glisten()


