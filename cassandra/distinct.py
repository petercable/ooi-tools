#!/usr/bin/env python

from multiprocessing import Pool, BoundedSemaphore
import sys
import time

import cassandra
from cassandra.cluster import Cluster
from cassandra.query import tuple_factory, SimpleStatement

lock = BoundedSemaphore(8)

class QueryManager(object):

    batch_size = 10

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

    def get_num_distinct(self, query, params):
        results = self.pool.map(_get_len_multiproc, [query] * count, self.batch_size)
        return results

    @classmethod
    def _execute_request(cls, query):
        now = time.time()
        stmt = SimpleStatement(query, consistency_level=cassandra.ConsistencyLevel.LOCAL_QUORUM)
        try:
            rval = list(cls.session.execute(stmt))
            print 'query returned: %d rows in %.2f secs' % (len(rval), time.time() - now)
        except Exception as e:
            print 'exception in query:', e
            rval = []
        return rval


def _get_len_multiproc(query):
    return len(QueryManager._execute_request(query))


if __name__ == '__main__':
    count = int(sys.argv[1])
    pool_size = int(sys.argv[2])

    cluster = Cluster(['192.168.144.101'])
    qm = QueryManager(cluster, pool_size)
    time.sleep(1.1 * pool_size)
    print 'Beginning query'

    distinct = qm.get_num_distinct('select subsite, node, sensor, method, stream from stream_metadata', count)
    failed = len([x for x in distinct if x == 0])
    total = len(distinct)
    print '%d/%d %.2f%%' % (total-failed, total, 100.0 * (total - failed) / total)
