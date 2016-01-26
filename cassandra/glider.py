#!/usr/bin/env python

import csv
import sys
import time

from cassandra.cluster import Cluster
from query_manager import QueryManager

if __name__ == '__main__':
    refdes = sys.argv[1]
    stream = sys.argv[2]
    pool_size = int(sys.argv[3])

    subsite, node, sensor = refdes.split('-', 2)

    cluster = Cluster(['192.168.144.101'])
    qm = QueryManager(cluster, pool_size)
    time.sleep(2 * pool_size)
    print 'Beginning query'

    print 'Finding all bins'
    bins = \
    qm.get_results('select method, bin from partition_metadata where stream=? and refdes=?', [(stream, refdes)])[0]
    params = [(subsite, node, sensor, method, bin) for method, bin in bins]

    fields = ['provenance', 'deployment', 'time', 'm_gps_lat', 'm_lat', 'm_gps_lon', 'm_lon', 'm_depth']
    for params, result in qm.get_async_results(
                    'select %s from %s where subsite=? and node=? and sensor=? and method=? and bin=?' % (
            ', '.join(fields), stream), params):
        subsite, node, sensor, method, bin = params
        rows = result.get()
        with open('%s-%s-%s-%s-%d.csv' % (subsite, node, sensor, method, bin), 'w') as fh:
            writer = csv.writer(fh)
            writer.writerow(fields)
            writer.writerows(rows)
