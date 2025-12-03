import requests
import base64
import io
import os
import uuid
import json
import warnings

from qiskit.providers import BackendV2, Options, JobV1 as Job
from qiskit_aer import AerSimulator
from qiskit import qpy
from qiskit_ibm_runtime.utils import RuntimeDecoder

class RemoteAerJob(Job):

    def __init__(self, backend, job_id, result):
        super().__init__(backend, job_id)
        self._result = result
    
    def result(self):
        return self._result
    
    def status(self):
        from qiskit.providers import JobStatus
        return JobStatus.DONE
    
    def submit(self):
        pass
    

class RemoteAerBackend(BackendV2):

    def __init__(self, name): 
        super().__init__(
            provider=None,
            name = name,
            description= "AerSimulator Implementation in k8s pod"
        )
        self._target = AerSimulator().target

        self.transpiler_url = os.getenv(
            'TRANSPILER_SERVICE_URL', 
            'http://transpiler-service:5002'  
        )
        
        print(f"Remote AerBackend configured with URL: {self.transpiler_url}")

    
    @classmethod
    def _default_options(cls):
        return Options(shots=1024)#, seed_simulator=None, method="automatic")
    
  
    def run(self, circuits, **options):
        # Get options
        shots = options.get('shots', 1024)

        # Serialize circuits using QPY
        if not isinstance(circuits, list):
            circuits = [circuits]

        
        print(f"Sending {len(circuits)} circuit(s) to remote simulator...")

        # use QPY to serialize 
        ## can we use RuntimeEncoder??
        with io.BytesIO() as fptr:
            qpy.dump(circuits, fptr)
            circuit_bytes = fptr.getvalue()
            circuits_b64 = base64.b64encode(circuit_bytes).decode('utf-8')

        # Send to transpiler
        try:
            response = requests.post(
                f"{self.transpiler_url}/transpile",
                
                json={
                    'circuits_qpy': circuits_b64,
                    'shots' : shots,
                    'backend_name' : self.name,
                   },
                
                timeout = 300                     
            )

            if response.status_code == 200:

                result_data = response.json()
                result_b64 = result_data['result']
                
                # Decode base64
                result_bytes = base64.b64decode(result_b64)
                result_json = result_bytes.decode("utf-8")

                # Deserialize using RuntimeDecoder
                result = json.loads(result_json, cls=RuntimeDecoder)

                print("Results received from remote simulator")
                job_id = str(uuid.uuid4())
                return RemoteAerJob(self, job_id, result)
            else:
                raise Exception(f"Simulator error: {response.text}")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to reach transpiler: {str(e)}")
        
    @property
    def target(self):
        return self._target

    
    @property
    def max_circuits(self):
        return None