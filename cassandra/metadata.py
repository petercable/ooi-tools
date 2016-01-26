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

rows = session.execute('select subsite, node, sensor, method, stream from stream_metadata')

with open('metadata.csv', 'w') as fh:
    csv.writer(fh).writerows(rows)
