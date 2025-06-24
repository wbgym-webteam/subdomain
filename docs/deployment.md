# Deployment Guide:

**Follow the steps of the [installation guide](installation.md) for the set-up!**

1. Create the service file

    `sudo nano /etc/systemd/system/subdomain.service`

2. Add the following configuration to the file and if necessary adapt some of the statements:

    ```sh
    [Unit] Description=Gunicorn instance to serve Flask app After=network.target

    [Service] User=webteam Group=www-data WorkingDirectory=/Subdomain/subdomain/src Environment="PATH=/Subdomain/venv/bin" ExecStart=/Subdomain/subdomain/src/.venv/bin/python -m gunicorn -w 4 -b 0.0.0.0:8000 main:app Restart=always

    [Install] WantedBy=multi-user.target
    ```

3. Start and Enable the Service:
    - Reload system and start the Flask service:

    ```sh
    sudo systemctl daemon-reload
    sudo systemctl start subdomain 
    sudo systemctl enable subdomain
    ```

4. Check Status: `sudo systemctl status subdomain`

5. Customize the Firewalls inside the Serverhosters terminal (copied from Digital ocean hosting platform)

6. Add these specific inbound firewall settings:

    ```sh
    Type: SSH; Protocol: TCP; Port Range: 22; Sources: All IPv4 and All IPv6
    Type: Custom; Protocol: TCP; Port Range: 8000; Sources: All IPv4 and All IPv6
    ```

7. Add these specific outbound firewall setting:

    ```sh
    Type: ICMP; Protocol: ICMP; Destinations: All IPv4 and All IPv6
    Type: All TCP; Protocol: TCP; Port Range: All ports; Destinations: All IPv4 and All IPv6
    Type: All UDP; Protocol: TCT; Port Range: All ports; Destinations: All IPv4 and All IPv6
    ```

8. Test the deployment --> Verify that the application if running (adapt the local host to the servers ipv4):

    ```sh
    curl http://localhost:8000
    ```