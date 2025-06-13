# Subdomain for _wbgym.de_

This is the repository, where the Weinberg Secondary School develops a subdomain for their website wbgym.de. It has multiple modules, which are all listen below. The Techstack used here is Python Flask for the backend, SQLite3 for the db and for the frontend plain HTML, CSS and JS.

## Modules

- **TdW** _(v1 Done)_: The module for the "Tag der Wissenschaften" (Day of Science). On this day some experts and grads are coming to the school and talk about a specific topic. The module here is for the students to select their presentation wishes.
- **SmS** _(Planning)_: The module for the "Schüler machen Schule" (Student teaches School). Here students can offer courses for other students, so it is another module for selection of courses. The specific format is yet to be determined.

## Documentation

Before the main page [wbgym.de](https://wbgym.de) switched to Wordpress as a CMS, there was Contao to manage the content and also these modules. The big issue here was the fact that there was no documentation at all. So the main goal of this rewrite is to document everything, so that the next generation of the webteam can easily understand and maintain the code.

The documentation is found in the `/docs` folder. It is written in Markdown and is generated with MkDocs. The documentation is hosted on [GitHub Pages](https://wbgym.github.io/subdomain/).

On these pages you will find all the information you need 💻.


#Deployment Guide:

    Clone the Game of Grapes repo: • Create new file called gog

    mkdir Subdomain

• Clone the GitHub repository

    Git Clone link/to/the/subdomain/repo

    Create the Virtual Environment: • Change directory to src

    Cd Subdomain/subdomain/src

• Create the Virtual Environment  Python3 -m venv .venv

• Activate the Virtual Environment

    Source .venv/bin/activate

    Install necessary Dependencies: • Create the service file

    Sudo nano /etc/systemd/system/subdomain.service

• Add the following configuration to the file and if necessary adapt some of the Statements:

[Unit] Description=Gunicorn instance to serve Flask app After=network.target

[Service] User=webteam Group=www-data WorkingDirectory=/Subdomain/subdomain/src Environment="PATH=/Subdomain/venv/bin" ExecStart=/Subdomain/subdomain/src/.venv/bin/python -m gunicorn -w 4 -b 0.0.0.0:8000 main:app Restart=always

[Install] WantedBy=multi-user.target

    Start and Enable the Service: • Reload system and start the Flask service  Sudo systemctl daemon-reload  Sudo systemctl start subdomain  Sudo systemctl enable subdomain

• Check Status • Sudo systemctl status subdomain

    Customize the Firewalls inside the Serverhosters terminal (copied from Digital ocean hosting platform) • Add these specific inbound firewall settings

    Type: SSH; Protocol: TCP; Port Range: 22; Sources: All IPv4 and All IPv6
    Type: Custom; Protocol: TCP; Port Range: 8000; Sources: All IPv4 and All IPv6

• Add these specific outbound firewall setting:

    Type: ICMP; Protocol: ICMP; Destinations: All IPv4 and All IPv6
    Type: All TCP; Protocol: TCP; Port Range: All ports; Destinations: All IPv4 and All IPv6
    Type: All UDP; Protocol: TCT; Port Range: All ports; Destinations: All IPv4 and All IPv6

    Test the deployment: • Verify that the application if running (adapt the local host to the servers ipv4)

    Curl http://localhost:8000
