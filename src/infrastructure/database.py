import requests  # Allow communications with TPP-DB API.
import yaml  # For reading private authentication data.


def read_auth():
    """.

    Reads authentication data from config.yml file.

    Returns a dictionary:
    tpp-token (long string)
    tpp-ip (e.g. 123.45.67.890
    tpp-port (e.g. 2000)
    tpp-url (e.g. https://tpp-ip:tpp-port/)
    tpp-headers (construct needed for communication)
    globus-token (globus key; not sure of format)

    """

    # Read tpp-db authentication
    config_file = "config.yml"  ###### NEED TO FIX THIS

    # Read config file for authentication info
    with open(config_file, "r") as file:
        authentication = yaml.safe_load(file)

    tpp_user = authentication["tpp-db"]["user"]
    tpp_pass = authentication["tpp-db"]["pass"]
    tpp_token = authentication["tpp-db"]["token"]
    tpp_ip = authentication["tpp-db"]["ip"]
    tpp_port = authentication["tpp-db"]["port"]
    tpp_url = "http://" + tpp_ip + ":" + tpp_port + "/"
    tpp_headers = {"Authorization": f"Bearer{tpp_token}"}

    # Read globus authentication
    globus_token = authentication["globus"]["token"]

    # Create dictionary for return.
    mydict = {
        "tpp_user": tpp_user,
        "tpp_pass": tpp_pass,
        "tpp_token": tpp_token,
        "tpp_ip": tpp_ip,
        "tpp_port": tpp_port,
        "tpp_url": tpp_url,
        "tpp_headers": tpp_headers,
        "globus_token": globus_token,
    }

    return mydict


def gen_token(length=3650):
    """.

    Generate a TPP database token.

    Author:    Sarah Burke-Spolaor
    Init Date: 23 May 2023

    This script can be run to instantiate a new user token. It is
    autoset to authenticate a token for 10 years. The user's
    config.yml must contain a correct IP and port.

    Input:
        length [expiry in days]

    Output:
        token [currently needs to be added to config file by hand]

    """

    # Read config file for authentication info
    auth = read_auth()
    tpp_token_call = auth["tpp_url"] + "token?=" + str(length)

    # Get the location of DATA_ID from TPP-DB
    token = requests.post(
        tpp_token_call,
        data={"username": auth["tpp_user"], "password": auth["tpp_pass"]},
    ).json()["access_token"]
    print(
        "Your new token is: "
        + token
        + "\n It will expire in "
        + str(length)
        + " days.\n"
    )
    print("Make sure you add it in to your config.yml file.\n")

    return token
