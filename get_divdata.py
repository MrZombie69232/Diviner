#!/usr/bin/env python
from __future__ import print_function, division
import pandas as pd
import sys
import os
from subprocess import call
from diviner.data_prep import index_by_time

# global list of columns to be extracted. will be adaptable by user later
columns = 'year,month,date,hour,minute,second,jdate,c,det,clat,clon,radiance,tb'.split(',')

def create_cmd_string(tstr, cstart, detstart, savedir='', cend=None, detend=None):
    if not cend:
        cend = cstart
    if not detend:
        detend = detstart
    pipes_root = '/u/marks/luner/pipes/rel'
    divdata_cmd = '/u/marks/luner/c38/rel/divdata'
    divdata_opt1 = 'daterange={0}'.format(tstr)
    divdata_opt2 = "clat=-90,90 c={0},{1} det={2},{3}".format(cstart, cend,
                                                            detstart, detend)
    pextract_cmd = os.path.join(pipes_root, 'pextract')
    pprint_cmd = os.path.join(pipes_root, 'pprint')
    pextract_opt = "extract={}".format(','.join(columns))
    pprint_opt = "titles=0 >"
    outfname = os.path.join(savedir, '{0}_divdata.csv'.format(tstr))
    cmd = "tcsh -c '{divdata_cmd} {divdata_opt1} {divdata_opt2}|"\
          "{pextract_cmd} {pextract_opt}|"\
          "{pprint_cmd} {pprint_opt} "\
          "{outfname}'".format(divdata_cmd=divdata_cmd,
                                 divdata_opt1=divdata_opt1,
                                 divdata_opt2=divdata_opt2,
                                 pextract_cmd=pextract_cmd,
                                 pextract_opt=pextract_opt,
                                 pprint_cmd=pprint_cmd,
                                 pprint_opt=pprint_opt,
                                 outfname=outfname)
    return cmd, outfname


def get_divdata(tstr, cstart, detstart, savedir='', cend=None, detend=None,
                create_hdf=True, drop_dates=True, keep_csv=False, save_hdf=False):
    """tstr in format %Y%m%d%H as usual.

    Parameters:
        tstr: In usual format %Y%m%d%H
        c, det:  Diviner channel and detector numbers
        savedir: path for the output files to be stored, default: current
        create_hdf: Parse the pprint text file into a pandas dataframe and return it to caller
            Default is True
        save_hdf: Save the pandas dataframe to disk, this is an option for the command-line 
            use of this tool. Dataframe handle in HDF file is 'df'. Default is False
        keep_csv: boolean to decide if to delete the tmp csv or to keep
        drop_dates: if you can't cope with datetime object, you can keep
            the time columns in the dataframe.
        
    Have to embed everything in a tc-shell call because otherwise
    the paths are not set-up correctly.
    """
    cmd, outfname = create_cmd_string(tstr, cstart, detstart, 
                                      savedir=savedir, cend=cend, detend=detend)
    print("Calling\n", cmd)
    sys.stdout.flush()
    call(cmd, shell=True)
    if os.path.exists(outfname):
        print("Created text file", outfname)
        print("Size:",os.path.getsize(outfname))
    else:
        print("Something went wrong, cannot find the output file.")
        return
    if create_hdf:
        print("Pandas parsing...")
        df = pd.read_csv(outfname, delim_whitespace=True)
        # first column is empty
        df.drop(df.columns[0], axis=1, inplace=True)
        # parse times and drop time columns
        df = index_by_time(df, drop_dates=drop_dates)
        if not keep_csv:
            print("Removing temporary text file", outfname)
            os.remove(outfname)
        if save_hdf:
            basename = os.path.basename(outfname)
            outname = os.path.splitext(basename)[0]+'.h5'
            print("Creating HDF file:",outname)
            df.to_hdf(outname,'df')
        return df


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Create divdata argument string, call divdata"
        " via subprocess.call() and save a text version created with pprint. Currently extracted"
        " data columns are: year,month,date,hour,minute,second,jdate,c,det,clat,clon,radiance,tb."
        " Parse and save into a HDF5 file with pandas if --create_hdf option is used."
        " Note that the optional arguments (starting with --) can be provided at any position"
        " in the command, e.g. at the end after timestring cstart and detstart.")

    # positional arguments
    parser.add_argument("timestring", default='%Y%m%d%H', 
                        help="In usual format %(default)s, for example 2010100412. "
                             "Currently no time-range implemented. Output filename will be "
                             "'timestring_divdata.csv'.")
    parser.add_argument('cstart', help="cstart. Diviner channel number to start from. "
                                       "Ranges between 1 and 9. Finish with --cend if required. "
                                       "Default is to only provide data for this channel.",
                        type=int, choices=range(1,10))
    parser.add_argument('detstart', help="detstart. Diviner detector number to start from. "
                                         "Finish with optional argument --detend if required. "
                                         "Default is to only provide data for this detector.",
                        type=int, choices=range(1,22))
    

    # optional arguments
    parser.add_argument('-s', '--savedir', help="Path to folder where to save the output file. "
                                          "Default is to use '', which means current folder.",
                        default='')
    parser.add_argument('--cend', help="Last Diviner channel to provide data for.",
                        type=int, choices=range(1,10))
    parser.add_argument('--detend', help="Last Diviner detector number to provide data for.",
                        type=int, choices=range(1,22))
    parser.add_argument('--create_hdf', help="Boolean flag. If active, parse CSV file with pandas"
                                             " and save HDF5 file with times parsed into "
                                             "datetime index. Dataframe handle in HDF file "
                                             "is 'df'.",
                        action='store_true')
    parser.add_argument('--keep_csv', help="Boolean flag. If active, don't delete the csv file "
                                           "if active after creating the HDF5 file.",
                        action='store_true')
    parser.add_argument('--keep_dates', help="Boolean. Drop the separate date and "
                                             "time columns when parsing time into a datetime "
                                             "object. Default is 'False'.",
                        action='store_true')
    parser.add_argument('-t', '--test', help='Print out the call command for verification and'
                                             ' exit.',
                        action='store_true')

    args = parser.parse_args()
    if len(args.timestring) != 10:
        print("\n Nope! timestring has to be 8 characters!\n")
        parser.print_help()
        sys.exit()
    if args.test:
        cmd = create_cmd_string(args.timestring, args.cstart, args.detstart, args.savedir,
                                cend=args.cend, detend=args.detend)
        print("Command verification:\n",cmd)
        sys.exit()
    get_divdata(args.timestring, args.cstart, args.detstart, args.savedir, 
                cend=args.cend, detend=args.detend,
                keep_csv=args.keep_csv, drop_dates=~args.keep_dates, 
                create_hdf=args.create_hdf, save_hdf=args.create_hdf)
