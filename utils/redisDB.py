import redis
import os
import time
import json


class RedisDB:

    def __init__(self, redis_host:str, redis_port: str):

        """
        Initialize Redis connection

        :param redis_host: Redis server hostname
        :param redis_port: Redis server port
        :raises: Exception if connection fails
        """


        self.redis_host = redis_host
        self.redis_port = int(redis_port)
        try:
            self.client = redis.Redis(
                host = self.redis_host,
                port = self.redis_port,
                decode_response = False
            )
            self.client.ping()
            print(f"✅ Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            print(f"❌ Failed to intialize Redis service")
            raise
    
    def create_job_data(self, job_id, circuit = None, 
                    results = None, ttl = 1200):
        """
        Create job data object in redis DB
        
        :param job_id: ID of the job
        :param circuit: quantum circuit (serialized)
        :param results: serialized results
        :param ttl: Time to Live
        :return: Created job data dictionary
        :raises: Exception if Redis operation fails
        """

        job_key = f"job:{job_id}"
        job_data = {
            "circuit" : circuit,
            "results" : results,
            # formated time 2026-01-09T06:39:00Z" --> T splits Date and time and Z stands for Zulu time
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),  
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        try:
            self.client.setex(
                job_key,
                ttl,
                json.dumps(job_data)
            )
            print("✅ Created job data in redis")
            return job_data
        except Exception as e:
            print("❌ Failed to create an entry in redis")
            raise
    
    def get_job_data(self, job_id):
        """
        Fetch job data with job id
    
        :param job_id: ID of the job
        :return: Job data dictionary or None if not found
        :raises: Exception if Redis operation fails
        """

        job_key = f"job:{job_id}"

        try:
            data = self.client.get(job_key)

            if not data:
                print(f"Job data not found : {job_id}")
                return None
            
            job_data = json.loads(data.decode("utf-8"))
            print(f"Sucessfully fetched job data : {job_id}")
            return job_data
        
        except json.JSONDecodeError as e:
            print(f"❌ Failed to decode job data for {job_id}: {e}")
            raise
        
        except Exception as e:
            print(f"❌ Failed to fetch the job data: {e}")
            raise
    
    def update_job_data(self, job_id, job_data, ttl = 1200):
    
        """
        Update job data in Redis
    
        :param job_id: ID of the job
        :param job_data: update job data dict.
        :param ttl: Time to Live
        :return: Updated job data dictionary
        :raises: Exception if Redis operation fails
        """

        job_key = f"job:{job_id}"

        job_data["updated_at"] = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())

        try:
            self.client.setex(
                job_key,
                ttl,
                json.dumps(job_data)
            )
        
        except Exception as e:
            print("❌ Failed to update the job data")
            raise

    def delete_job_data(self, job_id):
        """
        Delete job data from Redis
        
        :param job_id: Unique job identifier
        :return: True if deleted, False if didn't exist
        :raises: Exception if Redis operation fails
        """

        job_key = f"job:{job_id}"

        try:
            result = self.client.delete(job_key)
            if result:
                print(f"✅ Deleted job data: {job_id}")
                return True
            else:
                print(f"❌ Failed to delete job data: {job_id}")
                return False
        
        except Exception as e:
            print(f"Failed to fetch job data: {e}")
            raise

    def list_all_jobs(self):
        """
        List all job IDs currently in Redis
        
        :return: List of job IDs (strings)
        :raises: Exception if Redis operation fails
        """
        try:
            keys = self.client.keys("job:*")
            job_ids = [key.decode('utf-8').replace("job:", "") for key in keys]
            print(f"📋 Found {len(job_ids)} jobs in Redis")
            return job_ids
        except Exception as e:
            print(f"❌ Failed to list jobs: {e}")
            raise
    
    def close(self):
        """
        Close Redis connection
        """
        try:
            self.client.close()
            print("✅ Closed Redis connection")
        except Exception as e:
            print(f"⚠️  Error closing Redis connection: {e}")
