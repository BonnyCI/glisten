===============================
glisten
===============================

A baisc proxy from github events to gerrit events

This project listens for web hook events from github and relays them out to clients connected over an ssh connection. It also translates events from github events into something approximating gerrit events (a la stream-events). This is only meant as a shim to get zuul working with github.


----
setup
----


This project requires python3.

.. code-block:: shell

    $ virtualenv -p python3 venv
    $ source venv/bin/python


This project requires you to generate an ssh host key


.. code-block:: shell

    $ ssh-keygen -t rsa -b 4096 -f ssh_host_key

Running:

.. code-block:: shell

    $ pip install -r requirements.txt
    $ python glisten/glisten.py
    ======== Running on http://0.0.0.0:8080/ ========
    (Press CTRL+C to quit)
    SSH connection received from 127.0.0.1.
    SSH connection closed.



Use the webserver:

.. code-block:: shell

    $ curl http://localhost:8080
    Hello, Anonymous

Use the ssh server(password: secretpw):

.. code-block:: shell

    $ ssh -p 8022 user123@localhost
    Password:
    Welcome to my SSH server, user123!
    Connection to localhost closed.





------
notes
------


* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/glisten
* Source: http://git.openstack.org/cgit/openstack/glisten
* Bugs: http://bugs.launchpad.net/replace with the name of the project on launchpad


