import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime,timezone
from contextlib import contextmanager

class MetricsDB:
    def __init__(self):
        self.conn_params = {
            'host' : os.getenv('POSTGRES_HOST', 'localhost'),
            'port' : os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'postgres'),
            'user' : os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'mysecret')
        }

        self.conn = None
        self._connect()

    def _connect(self):
        """Establish connection to posgres DB"""
        
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.autocommit = True
        except Exception as e:
            raise RuntimeError(f"❌ Failed to connect to PostgreSQL: {e}")
    
    @contextmanager
    def get_cursor(self):
        """
        Context Manager for Database cursor. 
        Cursor is a database object used to 
        process data one row at a time.
        """
        if self.conn is None or self.conn.closed:
            self._connect()
        
        cursor = self.conn.cursor(cursor_factory = RealDictCursor)
        try:
            yield cursor
        finally:
            cursor.close()
    
    def create_job(self, job_id, backend_name, shots, circuit_depth=None, one_q_gate_count=None, two_q_gate_count = None):
        """ Create initial job entry when submitted"""
        with self.get_cursor() as cur:

            query = """
                INSERT INTO quantum_jobs(job_id, backend_name, shots, circuit_depth, one_q_gate_count, two_q_gate_count, status, submitted_at)
                VALUES (%(job_id)s, %(backend)s, %(shots)s, %(depth)s, %(q1)s, %(q2)s, 'submitted', %(time)s)
                ON CONFLICT (job_id) DO NOTHING
            """
            params = {
            'job_id': job_id,
            'backend': backend_name,
            'shots': shots,
            'depth': circuit_depth,
            'q1': one_q_gate_count,
            'q2': two_q_gate_count,
            'time': datetime.now(tz=timezone.utc) 
            }

            cur.execute(query,params)
            
    
    def update_transpiler_start(self, job_id):
        """ Mark transpilation started"""
        with self.get_cursor() as cur:
            query = """
            UPDATE quantum_jobs
            SET status = 'transpiling', transpile_start_at = %(time)s
            WHERE job_id = %(job_id)s
            """

            params = {
                'job_id' : job_id,
                'time' : datetime.now(tz=timezone.utc)
            }
            cur.execute(query,params)
    
    def update_transpile_complete(self, job_id, duration_ms, circuit_depth=None, one_q_gate_count = None, two_q_gate_count = None):
        """ Mark transpilation Ended """

        with self.get_cursor() as cur:
            query = """
            UPDATE quantum_jobs
            SET status = 'cr_created', 
                transpile_end_at = %(time)s,
                transpilation_duration_ms = %(duration)s,
                circuit_depth = COALESCE(%(depth)s, circuit_depth),
                one_q_gate_count = COALESCE(%(q1)s, one_q_gate_count),
                two_q_gate_count = COALESCE(%(q2)s, two_q_gate_count)
            WHERE job_id = %(job_id)s
            """
        
            params = {
                'job_id' : job_id,
                'time' : datetime.now(tz=timezone.utc),
                'duration': duration_ms,
                'depth' : circuit_depth,
                'q1' : one_q_gate_count,
                'q2' : two_q_gate_count

            }

            cur.execute(query, params)

    def update_simulation_start(self, job_id):
        """ Mark Start of Simulation """

        with self.get_cursor() as cur:

            query = """
            UPDATE quantum_jobs
            SET status = 'in progress',
                qpu_start_at = %(time)s
            WHERE job_id = %(job_id)s
            """

            params = {
                'job_id' : job_id,
                'time' : datetime.now(tz=timezone.utc)
            }

            cur.execute(query, params)
        
    def update_simulation_complete(self, job_id, pod_name = None):
        """ Mark simulation completed"""
        
        with self.get_cursor() as cur:

            query = """
            UPDATE quantum_jobs
            SET qpu_end_at = %(time)s,
                qpu_runtime_ms = EXTRACT(EPOCH FROM (%(time)s - qpu_start_at))*1000,
                pod_name = COALESCE(%(pod)s, pod_name)
            WHERE job_id = %(job_id)s
            """
            params = {
                "job_id" : job_id,
                "pod" : pod_name,
                "time" : datetime.now(tz=timezone.utc)
            }

            cur.execute(query, params)
    
    def update_job_complete(self, job_id):
        """ Mark job as completed"""

        with self.get_cursor() as cur:

            query = """
            UPDATE quantum_jobs
            SET status = 'completed',
                completed_at = %(time)s,
                total_runtime_ms = EXTRACT(EPOCH FROM (%(time)s - submitted_at)) * 1000
            WHERE job_id = %(job_id)s
            """
            params = {
                'job_id' : job_id,
                'time' : datetime.now(tz=timezone.utc)
            }
            cur.execute(query,params)

    
    def update_job_failed(self, job_id, error_message):
        """ Mark job as failed"""

        with self.get_cursor() as cur:

            query = """
            UPDATE quantum_jobs
            SET status = 'failed',
                error_message = %(error)s,
                completed_at = %(time)s,
                total_runtime_ms = EXTRACT(EPOCH FROM (%(time)s - submitted_at)) * 1000
            WHERE job_id = %(job_id)s
            """

            params = {
                'job_id' : job_id,
                'error' : error_message[:1000] if error_message else "Unknown error",
                'time' : datetime.now(tz=timezone.utc)
            }
            cur.execute(query,params)
    
    def record_resource_metrics(self, job_id, metric_name, metric_value, labels = None):
        """ Get all metrics for a specific job"""

        with self.get_cursor() as cur:
            
            query = """
            UPDATE resource_metrics
            SET metric_name = %(name)s,
                metric_value = %(value)s,
                labels = %(label)s
            WHERE job_id = %(job_id)s
            """

            params = {
                "job_id" : job_id,
                "name": metric_name,
                "value": metric_value,
                "label" : Json(labels or {})
            }

            cur.execute(query, params)

    def get_job_metrics(self, job_id):
        """ Get all metrics for a specific job"""
        with self.get_cursor() as cur:
            
            query = """
            SELECT * FROM quantum_jobs WHERE job_id = %(job_id)s
            """
            params = {
                "job_id" : job_id,
            }
            cur.execute(query, params)

            return cur.fetchone()
    
    def close(self):
        """ Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            print("✅ Closed PostgreSQL connection")
        
    

if __name__ == "__main__":

    metricsdb = MetricsDB()
    metricsdb.create_job(job_id='qjob-001', backend_name="ibm_fez", shots=1024)
    time.sleep(2)
    metricsdb.update_transpiler_start(job_id='qjob-001')
    print("✅ Job updated to transpiling!")
