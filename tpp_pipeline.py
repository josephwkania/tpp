# g!/usr/bin/env python3


""".
Assumptions: We are converting all input files to filterbanks after doing default RFI mitigation,
searching all spectra, only stokes I is searched, runs on default gpu Id, i.e 0,
adaptive scrunching on heimdall is enabled, candmaker runs on gpu 0,
FETCH uses model a and a probability of 0.1. Subbanded search is not yet implemented.

Print statements are to help with logging. Time commands too.

On the use of logging:
 - "debug" tag will be used for writing information that will be put into the database manager.
 - "info" will report status.
 - error and warnings will be used as intended.

This way, a database-ingestion script can easily scan and interpret logs.
"""

# TPPDB: determine job start
from datetime import datetime

time_start_UTC = datetime.utcnow()


import argparse
import glob
import your
from your import Your
import subprocess
import os
from your.utils.misc import YourArgparseFormatter
from timeit import default_timer as timer
import numpy as np
import pandas as pd


def dm_max(obslen, f_low, f_high):
    dm_h = (obslen * 10**3 / 4.15) * (1 / ((1 / f_low**2) - (1 / f_high**2)))
    return dm_h


def tpp_state(status):
    time_now = datetime.now()
    # TPPDB PUSH:
    #   time_now: update job_state_time to value of "time_now".
    #   job_state: update to value string "status"


def do_RFI_filter(filenames, basenames, your_object):
    # Reshma comment: Running your_writer with standard RFI mitigation. Clean file to run heimdall and candmaker on. Doesn't have to do RFI mitigation on each step. Also, filterbanks required for decimate.
    #!RESHMA TPPDB: Somewhere here (probably in your_writer.py) we will have to
    #!RESHMA TPPDB: get the code to update the RFI fraction and pre/post-zap RMS values.

    mask_start = timer()
    mask_cmd = (
        "your_rfimask.py -v -f "
        + str(filenames)
        + " -sk_sigma 4 -sg_sigma 4 -sg_frequency 15"
    )
    logger.debug("RFI MASK: command = " + mask_cmd)
    subprocess.call(mask_cmd, shell=True)
    mask_end = timer()
    logger.debug("RFI MASK: your_rfimask.py took " + str(mask_end - mask_start) + " s")
    mask_basename = str(basenames) + "_your_rfi_mask"
    killmask_file = f"{mask_basename}.bad_chans"
    with open(killmask_file, "r") as myfile:
        file_str = myfile.read()
    my_list = []  ##initializing a list
    for chan in file_str.split(
        " "
    ):  ##using split function to split, the list.this splits the value in index specified and return the value.
        my_list.append(chan)
    for chan in my_list:
        if chan == "":
            my_list.remove(chan)
    if len(my_list) == 0:
        logger.info(f"RFI MASK: No channels zapped")
    else:
        logger.debug(f"RFI MASK: No: of channels zapped = {len(my_list)}")
        logger.info(
            "RFI MASK: Percentage of channels zapped = "
            + str((len(my_list) / your_object.your_header.nchans) * 100)
            + " %"
        )


def do_heimdall(filenames, killmask):
    heimdall_start = timer()
    logger.info(
        "HEIMDALL:Using the raw data from"
        + str(filenames)
        + " for Heimdall and using the RFI mask "
        + str(killmask)
    )
    logger.info("HEIMDALL:Preparing to run Heimdall..\n")
    f_low = (center_freq + bw / 2) * 10 ** (-3)  # in GHz
    f_high = (center_freq - bw / 2) * 10 ** (-3)  # in GHz
    max_heimdall_dm = int(min(dm_max(obs_len, f_low, f_high), 10000))
    heimdall_cmd = (
        "your_heimdall.py -f "
        + str(filenames)
        + " -dm 0 "
        + str(max_heimdall_dm)
        + " -mask "
        + str(killmask)
    )
    subprocess.call(heimdall_cmd, shell=True)
    heimdall_end = timer()
    logger.debug(
        "HEIMDALL: your_heimdall.py took " + str(heimdall_end - heimdall_start) + " s"
    )


def do_candcsvmaker(filenames, basenames, killmask):
    candcsvmaker_start = timer()
    logger.info(
        "CANDCSVMAKER:Creating a csv file to get all the info from all the cand files...\n"
    )
    os.system(
        "python ../candcsvmaker.py -v -f ../"
        + str(filenames)
        + " -c *cand -k ../"
        + str(killmask)
    )
    #!RESHMA: Do we really need to include the pandas package just to read a csv? I wonder if we could avoid this dependancy and use something more common/portable. Or do you feel pandas is a good way to go?
    candidates = pd.read_csv(str(basenames) + ".csv")
    num_cands = str(candidates.shape[0])
    candcsvmaker_end = timer()
    logger.debug(
        "CANDMAKER: your_candmaker.py took "
        + str(candcsvmaker_end - candcsvmaker_start)
        + " s"
    )
    return num_cands


def do_your_candmaker(your_object):
    candmaker_start = timer()
    logger.info(
        "CANDMAKER:Preparing to run your_candmaker.py that makes h5 files.....\n"
    )
    if your_object.your_header.nchans <= 256:
        gg = -1
    else:
        gg = 0
    candmaker_cmd = "your_candmaker.py -v -c *csv -g " + str(gg) + " -n 4 -o ./h5/"
    subprocess.call(candmaker_cmd, shell=True)
    candmaker_end = timer()
    logger.debug(
        "CANDMAKER: your_candmaker.py took "
        + str(candmaker_end - candmaker_start)
        + " s"
    )


def do_fetch():
    fetch_start = timer()
    logger.info("FETCH:Preparing to run FETCH....\n")
    fetch_cmd = "predict.py -v -c . -m a -p 0.2"
    subprocess.call(fetch_cmd, shell=True)
    fetch_end = timer()
    logger.debug("FETCH: predict.py took " + str(fetch_end - fetch_start) + " s")


def do_your_h5plotter():
    h5_start = timer()
    logger.info("YOUR_H5PLOTTER: Preparing to plot h5 files....\n")
    plotter_cmd = "your_h5plotter.py -c results_a.csv"
    subprocess.call(plotter_cmd, shell=True)
    h5_end = timer()
    logger.debug("YOUR_H5PLOTTER: Took " + str(h5_end - h5_start) + " s")


if __name__ == "__main__":
    # Initiate Logging. Logging types  are:
    #    info (for blah blah blah)
    #    warn (for warnings)
    #    debug (for timestamp checks or other temp debugging)
    #    error (self explanatory)
    import logging

    logging.basicConfig(
        format="%(asctime)s  %(levelname)s: %(message)s", datefmt="%m-%d-%Y_%H:%M:%S"
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    # For some reason the below line needs to be included for logging to
    # function hereafter... haven't figured out why. - SBS
    logging.info("(This current line is of no consequence)")

    parser = argparse.ArgumentParser(
        prog="tpp_pipeline.py",
        description="Convert PSRFITS to FILTERBANK, makes a dedispersion plan, decimate the files if needed, runs HEIMDALL, makes h5s files of candidates, classifies using FETCH. For TPP pipeline usage only, turn on database manager with the secret code. ",
        formatter_class=YourArgparseFormatter,
    )
    parser.add_argument(
        "-f",
        "--files",
        help="Input files to be converted to an output format.",
        required=True,
        nargs="+",
    )
    parser.add_argument(
        "-t",
        "--tpp_db",
        help="Turn on updating to database manager. THIS IS FOR TPP OFFICIAL USE ONLY. To avoid mistaken turn-on, you must include the following argument to turn it on for real: mastersword",
        required=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Turn on DEBUG-level (general) logging.",
        required=False,
        action="store_true",
    )

    values = parser.parse_args()

    # Check logging level
    if values.verbose:
        logger.setLevel(logging.DEBUG)
        # For some reason the below line needs to be included for logging to
        # function hereafter... haven't figured out why. - SBS
    logging.info("(This current line is of no consequence)")

    # Read and check data files
    your_files = Your(values.files)
    logger.info("Reading raw data from " + str(values.files))
    filelist = your_files.your_header.filelist  # list of filenames
    filestring = " ".join(filelist)  # single string containing all file names
    basename = your_files.your_header.basename  # basename of the files
    center_freq = your_files.your_header.center_freq
    logger.info("The center frequency is " + str(center_freq) + " MHz")

    bw = your_files.your_header.bw
    logger.info("The bandwidth is " + str(bw) + " MHz")

    tsamp = your_files.your_header.native_tsamp
    logger.info("The native sampling time is " + str(tsamp) + " s")

    obs_len = your_files.your_header.native_nspectra * tsamp
    if obs_len >= 60:
        obs_len_min = obs_len / 60
        logger.info("Dataset length is " + str(obs_len_min) + " minutes")
    else:
        logger.info("Dataset length is " + str(obs_len) + " seconds")

    # TPPDB: !!!!! May need to read declination from the TPPDB, not the file itself; Graham says that sometimes declination is listed with seconds>60. !!!!!!

    # TPPDB: !!!!! NEED TO ADD AN INTERNAL CHECK HERE TO MAKE SURE THAT THE DATA INFORMATION READ IS SANE!!!

    # Check Database Manager connection request
    logger.info("My database writer value is " + str(values.tpp_db))
    db_on = False
    if values.tpp_db is not None:
        db_password = values.tpp_db
        if db_password != "mastersword":
            logger.error(
                "******************************************************************"
            )
            logger.error(
                "***** It looks like you tried to turn on the TPP Manager but *****"
            )
            logger.error(
                "*****        provided the wrong password. Exiting now.       *****"
            )
            logger.error(
                "******************************************************************"
            )
            exit()
        elif db_password == "mastersword":
            logger.warning(
                "******************************************************************"
            )
            logger.warning(
                "*****Pipeline results will be pushed to TPP Database Manager.*****"
            )
            logger.warning(
                "*****      If this is unintentional, abort your run now.     *****"
            )
            logger.warning(
                "******************************************************************"
            )
            db_on = True
    else:
        logger.info("No connections will be made to TPP Database Manager.")
        db_on = False

    # Determine node_name and current working directory
    node_name = os.uname()[1]
    cwd = os.getcwd()
    logger.info(
        "Processing in directory "
        + str(cwd)
        + " on node "
        + str(node_name)
        + ", began at UTC "
        + str(time_start_UTC)
    )

    if db_on:
        tpp_state("started")
        # TPPDB_PUSH:
        #   time_start_UTC: Update job_start based on previously determined "time_start_UTC"
        #   time_now to time_start_UTC
        #   node_name: TPPDB: DETERMINE NODE NAME, submit to OUTCOMES node_name
        #   current_working_directory: TPPDB: Determine current working directory, submit to OUTCOMES working_directory

    ############## ############## ##############
    ##############  YOUR_WRITER   ##############
    ############## ############## ##############
    # Runs RFI filtering; also converts psrfits-format files to an RFI-filtered filterbank-format file.

    logger.info("RFI MASK:Preparing to run your_rfimask to create an RFI mask\n")

    if db_on:
        tpp_state("your_rfimask")

    try:
        do_RFI_filter(filestring, basename, your_files)
    except Exception as error:
        if db_on:
            status = "ERROR in your_rfimask: " + error
            tpp_state(status)
        else:
            print(error)
            logger.debug(error)
    """
    #your_fil_object=Your(your_files.your_header.basename+"_converted.fil")
    #logger.info()
    native_nspectra=your_files.your_header.native_nspectra
    fil_nspectra=your_fil_object.your_header.native_nspectra
    if native_nspectra==fil_nspectra:
        logger.warning('All spectra written to Filterbank')
    else:
        logger.warning('Not all spectra is written to Filterbank')
    logger.debug('Writer done, moving on')

  
    ############## ############## ############## 
    ##############     DDPLAN     ############## 
    ############## ############## ############## 
    # Will be used for low-frequency data.


# Running DDplan.py
if center_freq<1000: 
logger.warning("Low frequency (< 1 GHz) data. Preparing to run DDplan.py....\n")

    ddplan_cmd="DDplan.py -o "+your_files.your_header.basename+"_ddplan -l 0 -d 3600 -f "+str(center_freq)+ " -b "+str(np.abs(bw))+ " -n "+str(your_files.your_header.native_nchans)+ " -t"+str(tsamp)+" -w >"+ your_files.your_header.basename+"_ddplan.txt" 
    subprocess.call(ddplan_cmd,shell=True)
    logger.info('DDplan completed. A text file is created\n')
    # Read the input from the text file and decimate. To be fixed....
    deci_cmd="decimate *fil -t 2 -c 1 >"+str(your_files.your_header.basename)+"_decimated.fil" 
    subprocess.call(deci_cmd,shell=True)
    """

    ############## ############## ##############
    ##############    HEIMDALL    ##############
    ############## ############## ##############
    mask_basename = str(basename) + "_your_rfi_mask"
    killmask_file = f"{mask_basename}.bad_chans"
    if db_on:
        tpp_state("heimdall")
    try:
        do_heimdall(filestring, killmask_file)
    except Exception as error:
        if db_on:
            status = "ERROR in heimdall: " + error
            tpp_state(status)
        else:
            print(error)

    ############## ############## ##############
    ##############  CANDCSVMAKER  ##############
    ############## ############## ##############
    if db_on:
        tpp_state("candcsvmaker")

    # Go to the new directory with the heimdall cands
    cand_dir = os.chdir(os.getcwd() + "/" + str(basename))
    logger.debug("DIR CHECK:Now you are at " + str(os.getcwd()) + "\n")

    try:
        num_cands = do_candcsvmaker(filestring, basename, killmask_file)
    except Exception as error:
        if db_on:
            status = "ERROR in candcsvmaker: " + error
            tpp_state(status)
        else:
            print(error)
            logger.debug(error)

    logger.info("CHECK:Number of candidates created = " + num_cands)

    #!HTPPDB: I think this is a good place to determine and update
    # TPPDB: fetch_histogram (or perhaps we can get candcsvmaker to report it to
    # TPPDB: avoid re-reading the csv file). Same goes for n_members,
    # TPPDB: n_detections, n_candidates. I think we could easily add an accounting
    # TPPDB: of those things all into candcsvmaker.py.

    # Create a directory for the h5s
    try:
        os.makedirs("h5")
    except FileExistsError:
        pass

    """

    NOTE IT IS HERE THAT WE NEED TO DO COORDINATE CORRECTION FOR DRIFTSCAN DATA
    !!!
    """

    ############## ############## ##############
    ############## YOUR_CANDMAKER ##############
    ############## ############## ##############
    if db_on:
        tpp_state("your_candmaker")

    try:
        do_your_candmaker(your_files)
    except Exception as error:
        if db_on:
            status = "ERROR in your_candmaker: " + error
            tpp_state(status)
        else:
            print(error)

    # Go into h5 directory, check all h5 files created appropriately.
    os.chdir(os.getcwd() + "/h5")
    logger.debug("DIR CHECK:Now you are at " + str(os.getcwd()) + "\n")

    dir_path = "./"
    num_h5s = len(glob.glob1(dir_path, "*.h5"))

    if int(num_h5s) == int(num_cands):
        logger.debug("CHECK:All candidiate h5s created")
    else:
        logger.warning("POSSIBLE ISSUE: Not all cand h5s are created")
        #!RESHMA can you check if you agree that this is an exit-able offense?
        if db_on:
            logger.error("ERROR in h5 file creation: Not all cand h5s were created.")
            tpp_state("ERROR in h5 file creation: Not all cand h5s were created.")

    ############## ############## ##############
    ##############     FETCH      ##############
    ############## ############## ##############
    if db_on:
        tpp_state("fetch")

    try:
        do_fetch()
    except Exception as error:
        if db_on:
            status = "ERROR in fetch: " + error
            tpp_state(status)
        else:
            print(error)

    ############## ############## ##############
    ##############   H5 PLOTTER   ##############
    ############## ############## ##############
    if db_on:
        tpp_state("your_h5plotter")

    if os.path.isfile("results_a.csv"):
        logger.info("FETCH: FETCH ran successfully")

        try:
            do_your_h5plotter()
        except Exception as error:
            if db_on:
                status = "ERROR in your_h5plotter: " + error
                tpp_state(status)
            else:
                print(error)
        fetchcsv = pd.read_csv("results_a.csv")
        fetch_positives = np.where(fetchcsv["label"] == 1.0)[0].shape[0]
        png_counter = len(glob.glob1(dir_path, "*.png"))
        if fetch_positives == png_counter:
            logger.debug("H5PLOTTER:All pngs are created")
        else:
            logger.warning("H5PLOTTER: Not all pngs are created")
        #!H TPPDB: gather all relevant info for RESULTS and push every
        # TPPDB: detection to database. Is there a way to do this in bulk?
        # TPPDB: ---ask Bikash. We will need to make sure we catch
        # TPPDB: range/format issues here and report them appropriately.

    else:
        logger.warning("FETCH:FETCH did not create a csv file")

    # TPPDB: Determine output directory and submit to OUTCOMES
    # TPPDB: output_directory? --- we will not do this here if the job launcher
    # TPPDB: handles the transfer and disk management.

    # TPPDB: at any point of failure above, the job_end should be updated and job_state should be updated to "ERROR: " with a relevant message.

    ############## ############## ##############
    ##############     WRAP-UP    ##############
    ############## ############## ##############
    tpp_state("complete")
    # TPPDB PUSH:
    #    job_end: update job_end to value of "time_now".

    # (All done).
