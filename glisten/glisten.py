#!/usr/bin/env python3.5
#
# Copyright (c) 2016 by Ron Frederick <ronf@timeheart.net>.
# Copyright (c) 2016 IBM
# All rights reserved.
#
# This program and the accompanying materials are made available under
# the terms of the Eclipse Public License v1.0 which accompanies this
# distribution and is available at:
#
#     http://www.eclipse.org/legal/epl-v10.html
#
# Contributors:
#     Ron Frederick - examples used in initial implementation,
#                     API, and documentation
#     Spencer Krum  - glisten code

from aiohttp import web
import asyncio
import asyncssh
import crypt
import sys

# To run this program, the file ``ssh_host_key`` must exist with an SSH
# private key in it to use as a server host key. An SSH host certificate
# can optionally be provided in the file ``ssh_host_key-cert.pub``.
passwords = {'guest': '',                 # guest account with no password
             'user123': 'qV2iEadIGV2rw'   # password of 'secretpw'
             }


class SSHServer(asyncssh.SSHServer):
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


class Glisten(object):
    def __init__(self):
        self.clients = []
        self.loop = asyncio.get_event_loop()
        self.ssh_server = None
        self.web_app = None

    def start(self):
        # SSH server
        self.ssh_server = self._start_sshd()
        self.loop.run_until_complete(self.ssh_server)

        # http server
        app = web.Application()
        app.router.add_get('/', self._handle_root_get)
        app.router.add_post('/post', self._handle_webhook_post)
        self.web_app = app

        # this calls run_until_complete somewhere
        web.run_app(app)

    async def _start_sshd(self):
        return await asyncssh.create_server(
            SSHServer, '', 8022,
            server_host_keys=['ssh_host_key'],
            session_factory=self._handle_ssh_session)

    async def _handle_ssh_session(self, stdin, stdout, stderr):
        try:
            self.clients.append((stdin, stdout, stderr))
            stdout.write('Welcome to my SSH server, %s!\n' % 'human unit')
            stdout.channel.exit(0)
        finally:
            self.clients.remove((stdin, stdout, stderr))

    async def _handle_root_get(self, request):
        name = request.match_info.get('name', "Anonymous")
        text = "Hello, " + name
        return web.Response(text=text)

    async def _handle_webhook_post(self, request):
        # WARNING: don't do this if you plan to receive large files!
        project_name = await request.json()

        for client in self.clients:
            client[1].write("Event: {0}\n".format(project_name['project_name']))

        text = "Data Recieved!"

        return web.Response(text=text)


def main():
    g = Glisten()
    g.start()


if __name__ == "__main__":
    main()
