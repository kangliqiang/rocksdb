#! /usr/bin/env python
import os
import sys
import time
import shlex
import getopt
import logging
import tempfile
import subprocess

# This python script runs db_stress multiple times with kill_random_test
# that causes leveldb to crash at various points in code.
# It also has test-batches-snapshot ON so that basic atomic/consistency
# checks can be performed.
#
def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hd:t:k:o:b:")
    except getopt.GetoptError:
        print str(getopt.GetoptError)
        print "db_crashtest2.py -d <duration_test> -t <#threads> " \
            "-k <kills with prob 1/k> -o <ops_per_thread> "\
            "-b <write_buffer_size>\n"
        sys.exit(2)

    # default values, will be overridden by cmdline args
    kill_random_test = 97  # kill with probability 1/97 by default
    duration = 6000  # total time for this script to test db_stress
    threads = 32
    ops_per_thread = 200000
    write_buf_size = 4 * 1024 * 1024

    for opt, arg in opts:
        if opt == '-h':
            print "db_crashtest2.py -d <duration_test> -t <#threads> " \
                "-k <kills with prob 1/k> -o <ops_per_thread> "\
                "-b <write_buffer_size>\n"
            sys.exit()
        elif opt == ("-d"):
            duration = int(arg)
        elif opt == ("-t"):
            threads = int(arg)
        elif opt == ("-k"):
            kill_random_test = int(arg)
        elif opt == ("-i"):
            interval = int(arg)
        elif opt == ("-o"):
            ops_per_thread = int(arg)
        elif opt == ("-b"):
            write_buf_size = int(arg)
        else:
            print "unrecognized option " + str(opt) + "\n"
            print "db_crashtest2.py -d <duration_test> -t <#threads> " \
                "-k <kills with prob 1/k> -o <ops_per_thread> " \
                "-b <write_buffer_size>\n"
            sys.exit(2)

    exit_time = time.time() + duration

    dirpath = tempfile.mkdtemp()

    print("Running whitebox-crash-test with \ntotal-duration=" + str(duration)
          + "\nthreads=" + str(threads) + "\nops_per_thread="
          + str(ops_per_thread) + "\nwrite_buffer_size="
          + str(write_buf_size) + "\n")

    # kill in every alternate run. toggle tracks which run we are doing.
    toggle = True

    while time.time() < exit_time:
        run_had_errors = False
        print "Running db_stress \n"

        if toggle:
            # since we are going to kill anyway, use more ops per thread
            new_ops_per_thread = 100 * ops_per_thread
            killoption = '--kill_random_test=' + str(kill_random_test)
        else:
            new_ops_per_thread = ops_per_thread
            killoption = ''

        toggle = not toggle

        cmd = ['./db_stress \
                --test_batches_snapshots=1 \
                --ops_per_thread=0' + str(new_ops_per_thread) + ' \
                --threads=0' + str(threads) + ' \
                --write_buffer_size=' + str(write_buf_size) + ' \
                --destroy_db_initially=0 ' + killoption + ' \
                --reopen=0 \
                --readpercent=50 \
                --db=' + dirpath + ' \
                --max_key=10000']

        popen = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 shell=True)
        stdoutdata, stderrdata = popen.communicate()
        retncode = popen.returncode
        msg = ("kill option = {0}, exitcode = {1}".format(
               killoption, retncode))
        print msg
        print stdoutdata

        expected = False
        if (killoption == '') and (retncode == 0):
            # we expect zero retncode if no kill option
            expected = True
        elif killoption != '' and retncode < 0:
            # we expect negative retncode if kill option was given
            expected = True

        if not expected:
            print "TEST FAILED!!!\n"
            sys.exit(1)

        stdoutdata = stdoutdata.lower()
        if ('error' in stdoutdata) or ('fail' in stdoutdata):
            print "TEST FAILED!!!\n"
            sys.exit(2)
        time.sleep(1)  # time to stabilize after a kill

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))