#!/usr/bin/env python

import uuid
import os
import csv
import sys
import time
import ntplib

import cassandra
from cassandra.cluster import Cluster
from cassandra.query import tuple_factory, SimpleStatement
from cassandra.concurrent import execute_concurrent_with_args

cluster = Cluster(['192.168.144.101'])
session = cluster.connect('ooi')

def insert_part_md(subsite, node, sensor, method, b, count, start, stop):
    # stream text, refdes text, method text, bin bigint, store text, first double, last double, count bigint,
    session.execute ('insert into partition_metadata (stream, refdes, method, bin, store, first, last, count) values (%s, %s, %s, %s, %s, %s, %s, %s)',
        ('glider_gps_position', '-'.join((subsite, node, sensor)), method, b, 'cass', start, stop, count))

def insert_stream_md(subsite, node, sensor, method, count, start, stop):
    # ( subsite text, node text, sensor text, method text, stream text, count bigint, first double, last double,
    session.execute ('insert into stream_metadata (subsite, node, sensor, method, stream, count, first, last) values (%s, %s, %s, %s, %s, %s, %s, %s)',
        (subsite, node, sensor, method, 'glider_gps_position', count, start, stop))

def insert_bin(ps, dname, fname):
    subsite, node, sensor1, sensor2, method, b = fname.split('.')[0].split('-')
    sensor = sensor1 + '-' + sensor2
    with open(os.path.join(dname, fname)) as fh:
        reader = csv.reader(fh)
        next(reader)
        times = []
        rows = []
        for p, d, t, gps_lat, lat, gps_lon, lon, depth in reader:
            if all([gps_lat, gps_lon]):
                p = uuid.UUID(p)
                d = int(d)
                t = float(t)
                gps_lat = float(gps_lat)
                gps_lon = float(gps_lon)
                b = int(b)
                i = uuid.uuid4()
                times.append(t)
                rows.append((i, subsite, node, sensor, method, p, d, b, t, gps_lat, gps_lon))
        execute_concurrent_with_args(session, ps, rows)
        insert_part_md(subsite, node, sensor, method, b, len(times), min(times), max(times))
        return times

if __name__ == '__main__':
    dname = sys.argv[1]
    ps = session.prepare('insert into glider_gps_position (id,subsite,node,sensor,method,provenance,deployment,bin,time,m_gps_lat,m_gps_lon) values (?,?,?,?,?,?,?,?,?,?,?)')
    times = []
    for index, fname in enumerate(os.listdir(dname)):
        subsite, node, sensor1, sensor2, method, b = fname.split('.')[0].split('-')
        sensor = sensor1 + '-' + sensor2
        print index, fname
        times.extend(insert_bin(ps, dname, fname))
    insert_stream_md(subsite, node, sensor, method, len(times), min(times), max(times))

