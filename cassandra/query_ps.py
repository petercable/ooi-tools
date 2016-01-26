#!/usr/bin/env python

from multiprocessing import Pool, BoundedSemaphore
import sys
import time

import cassandra
from cassandra.cluster import Cluster
from cassandra.query import tuple_factory, SimpleStatement

lock = BoundedSemaphore(6)

class QueryManager(object):

    batch_size = 1

    def __init__(self, cluster, process_count=None):
        self.pool = Pool(processes=process_count, initializer=self._setup, initargs=(cluster,))

    @classmethod
    def _setup(cls, cluster):
        with lock:
            cls.session = cluster.connect('ooi')
            cls.session.row_factory = tuple_factory
            print 'worker ready'

    def close_pool(self):
        self.pool.close()
        self.pool.join()

    @classmethod
    def prepare(cls, query):
        ps = cls.session.prepare(query)
        ps.consistency_level=cassandra.ConsistencyLevel.LOCAL_QUORUM
        return ps

    def get_results(self, query, params):
        results = self.pool.map(_get_multiproc, [(query,p) for p in params], self.batch_size)
        return results

    def get_num_results(self, query, params):
        results = self.pool.map(_get_len_multiproc, [(query,p) for p in params], self.batch_size)
        return results

    @classmethod
    def _execute_request(cls, query, params):
        now = time.time()
        try:
            rval = list(cls.session.execute(query, params))
            print 'query returned: %d rows in %.2f secs' % (len(rval), time.time() - now)
            return rval
        except Exception as e:
            print 'exception running query:', e
            return []

    @classmethod
    def get_stats(cls):
        return cluster.metrics.request_timer


def _get_multiproc(params):
    query, params = params
    query = QueryManager.prepare(query)
    return QueryManager._execute_request(query, params)

def _get_len_multiproc(params):
    query, params = params
    query = QueryManager.prepare(query)
    return len(QueryManager._execute_request(query, params))

def _get_stats():
    return QueryManager.get_stats()


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

values = qm.get_num_results('select * from %s where subsite=? and node=? and sensor=? and method=? and bin=?' % stream, params)
print values
