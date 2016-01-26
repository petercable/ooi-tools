#!/usr/bin/env python

import sys
import time

from cassandra.cluster import Cluster
from query_manager import QueryManager

refdes = sys.argv[1]
stream = sys.argv[2]
count = int(sys.argv[3])
pool_size = int(sys.argv[4])

subsite, node, sensor = refdes.split('-', 2)

cluster = Cluster(['192.168.144.101'], metrics_enabled=True)
qm = QueryManager(cluster, pool_size)
time.sleep(1 * pool_size)
print 'Beginning query'

bins = qm.get_results('select method, bin from partition_metadata where stream=? and refdes=?', [(stream, refdes)])[0]
bins.sort()
while len(bins) < count:
    bins = bins + bins
params = [(subsite, node, sensor, method, bin) for method, bin in bins[:count]]

values = qm.get_num_results('select * from %s where subsite=? and node=? and sensor=? and method=? and bin=?' % stream,
                            params)
print values
