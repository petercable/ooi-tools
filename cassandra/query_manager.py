import cassandra
import time

from multiprocessing import Pool, BoundedSemaphore

from cassandra.query import tuple_factory


class QueryManager(object):
    batch_size = 1
    lock = BoundedSemaphore(6)

    def __init__(self, cluster, process_count=None):
        self.pool = Pool(processes=process_count, initializer=self._setup, initargs=(cluster,))

    @classmethod
    def _setup(cls, cluster):
        cls.cluster = cluster
        with cls.lock:
            cls.session = cluster.connect('ooi')
            cls.session.row_factory = tuple_factory
            print 'worker ready'

    def close_pool(self):
        self.pool.close()
        self.pool.join()

    @classmethod
    def prepare(cls, query):
        ps = cls.session.prepare(query)
        ps.consistency_level = cassandra.ConsistencyLevel.LOCAL_QUORUM
        return ps

    def get_results(self, query, params):
        results = self.pool.map(_get_multiproc, [(query, p) for p in params], self.batch_size)
        return results

    def get_num_results(self, query, params):
        results = self.pool.map(_get_len_multiproc, [(query, p) for p in params], self.batch_size)
        return results

    def get_async_results(self, query, params):
        results = []
        for p in params:
            results.append((p, self.pool.apply_async(_get_async_multiproc, (query, p))))
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
        return cls.cluster.metrics.request_timer


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


def _get_async_multiproc(query, params):
    query = QueryManager.prepare(query)
    return list(QueryManager._execute_request(query, params))
