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
    
    def update_job_complete(self, job_id):

        with self.get_cursor() as cur:

            query = """
            UPDATE quantum_jobs
            SET status = 'completed',
                completed_at = %(time)s,
                total_duration_ms = EXTRACT(EPOCH FROM (%(time)s - submitted_at)) * 1000
            WHERE job_id = %(job_id)s
            """
            params = {
                'job_id' : job_id,
                'time' : datetime.now(tz=timezone.utc)
            }
            cur.execute(query,params)

    

if __name__ == "__main__":

    metricsdb = MetricsDB()
    metricsdb.create_job(job_id='qjob-001', backend_name="ibm_fez", shots=1024)
    time.sleep(2)
    metricsdb.update_transpiler_start(job_id='qjob-001')
    print("✅ Job updated to transpiling!")
