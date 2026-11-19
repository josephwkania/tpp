""".
TPP Job Launcher: Thorny Flat Edition


Author:    Sarah Burke-Spolaor
Init Date: 22 May 2023

This code will be called by the Globus file transfer script (intended
to be written by Joe Glaser). The purpose of this code is to:

 - Be runnable on Thorny Flat (and potentially easily repurposed for
   Dolly Sods in the future).

 - Access the TPP database manager (TPP-DB).

 - Identify the location of requested data from TPP-DB.

 - Set up the job command and call Slurm.

 - Also initiate a Globus transfer of H5 files to JBOD at the end of
   the script? Or will this be done in the processing script? - Joe G
   to comment.

"""

import requests  # Allow communications with TPP-DB API.
import subprocess  # To call sbatch/slurm.
import yaml  # For reading private authentication data.


# Data ID requested by user (unique identifier in DM of file to be processed).
data_id = ""  ###### NEED TO FIX THIS - JOE TO BUILD.
config_file = ""  ###### NEED TO FIX THIS ONCE SETUP FILE IS DONE.

# Read config file for authentication info
with open(config_file, "r") as file:
    authentication = yaml.safe_load(file)

config = "/Users/sbs/soft/tpp/myconf.yml"  ###### NEED TO FIX THIS
tppdb_ip = authentication["tpp-db"]["url"]
tppdb_port = authentication["tpp-db"]["port"]
user_token = authentication["tpp-db"]["token"]
globus_token = authentication["globus"]["token"]


# Set up TPP-DB communications.
tppdb_base = "http://" + tppdb_ip + ":" + tppdb_port
tppdb_data = tppdb_base + "/data"
headers = {"Authorization": f"Bearer{token}"}


# Get the location of DATA_ID from TPP-DB
#### NOTE SARAH NEEDS TO ADD A COMMS FAILURE CHECK HERE. Do we want to write a subprocess elsewhere that does basic TPP-DB communications success checks?
mydata = requests.get(tppdb_data + "/" + data_id, headers=headers).json()
filename = mydata["location_on_filesystem"]


# Use command line to call slurm.
subprocess.run(
    [
        "sbatch",
        '--time=5-23:45:00 --nodes=1 --ntasks-per-node=10 --job-name="Reshma" --partition=thepartitiontouse --wrap="SINGULARITY CALL ; COMMAND TO RUN',
    ]
)  ###### NEED TO FIX THIS
