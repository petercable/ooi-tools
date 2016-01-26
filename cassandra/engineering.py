#!/usr/bin/env python

import uuid
import os
import csv
import sys
import time
import ntplib
import pprint

import cassandra
from cassandra.cluster import Cluster
from cassandra.query import tuple_factory, SimpleStatement
from cassandra.concurrent import execute_concurrent_with_args

cluster = Cluster(['192.168.144.101'])
session = cluster.connect('ooi')

args = sys.argv[1:6]
args[4] = int(args[4])
rows = list(session.execute('select * from glider_eng_recovered where subsite=%s and node=%s and sensor=%s and method=%s and bin=%s', args))

with open('engineering.csv', 'w') as fh:
    row = rows[0]
    writer = csv.writer(fh)
    writer.writerow(row._fields)
    writer.writerows(rows)
