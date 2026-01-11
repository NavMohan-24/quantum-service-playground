import os,sys,io,base64,json, traceback

from qiskit import qpy
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit_ibm_runtime.utils import RuntimeEncoder
from qiskit_aer import AerSimulator
from kubernetes import client, config
from utils.redisDB import RedisDB


def load_kube_config():
    """
    load kubernetes configuration (in cluster)
    """
    try:
        # loads service account token
        # kubernetes add the token to access the service account
        # in a standard path /var/run/secrets/kubernetes.io/serviceaccount/token
        # token is used while updating the CR.
        config.load_incluster_config()

        print("✅ Loaded in-cluster Kubernetes config")
    
    except Exception as e:
        print(f"failed to load kube config: {e}")
        sys.exit(1)

# Initialize service and cache backends at startup
service = None

def init_ibm_service():
    """
    Initialize Qiskit Runtime Service
    """
    global service
    IBM_API_KEY = os.getenv('IBM_API_KEY')
    IBM_INSTANCE = os.getenv('IBM_INSTANCE')  

    print("API KEY :",repr(IBM_API_KEY))
    print("Instance :",repr(IBM_INSTANCE))
    try:
        if IBM_API_KEY:
            print("Initializing IBM Quantum service...")
            service = QiskitRuntimeService(
                channel="ibm_quantum_platform",
                token=IBM_API_KEY,
                instance=IBM_INSTANCE
            )
            print("✅ IBM service initialized")
        else:
            print("⚠️ No IBM API key - using AerSimulator only")
    except Exception as e:
        print(f"❌ Failed to init IBM service: {e}")
        service = None



def get_env_vars():
    """
    Extract env variables to run the job
    """
    return {
        'shots': int(os.getenv('SHOTS', '1024')),
        'backend_name': os.getenv('BACKEND_NAME', 'aer-simulator'),
        'job_id': os.getenv('JOB_ID', 'unknown'),
        'quantum_job_name': os.getenv('QUANTUM_JOB_NAME'),
        'quantum_job_namespace': os.getenv('QUANTUM_JOB_NAMESPACE', 'default'),
        'redis_host' : os.getenv("REDIS_HOST", "redis-service"),
        'redis_port' : os.getenv("REDIS_PORT", "6379")
    }

def deserialize_circuits(circuits_b64):
    """
    Deserialize the base64 encoded quantum circuit
    
    :param circuits_b64: base64 encoded quantum circuit
    """
    try:
        circuit_bytes = base64.b64decode(circuits_b64)
        with io.BytesIO(circuit_bytes) as fptr:
            circuits = qpy.load(fptr)
        print(f"✅ Deserialized {len(circuits)} circuit(s)")
        return circuits
    except Exception as e:
        raise ValueError(f"Failed to deserialize circuits: {e}")

def serialize_results(results):
    """
    Serialize the result to base64-encoded JSON
    
    :param results: PrimitiveResult object.
    """
    result_json = json.dumps(results, cls=RuntimeEncoder)
    result_bytes = result_json.encode("utf-8")
    result_b64 = base64.b64encode(result_bytes).decode("utf-8")
    return result_b64

def run_simulation(circuits, shots, backend_name):
    """
    Execution of the circuit with AerSimulator
    
    :param circuits: Quantum Circuit
    :param shots: Number of shots for sampling
    :param backend_name: Name of the backend
    """

    print(f"🔬 Starting simulation with {shots} shots on {backend_name}")

    if backend_name == "aer-simulator":
        simulator = AerSimulator()
    else:
        if service is None:
            init_ibm_service()
        
        if service is None:
            raise RuntimeError("IBM Quantum service not available")
        
        backend = service.backend(backend_name)
        simulator = AerSimulator.from_backend(backend)
    
    sampler = SamplerV2(mode=simulator)
    # Run simulation
    job = sampler.run(pubs=circuits, shots=shots)
    results = job.result()
    print("✅ Simulation completed successfully")
    return results

def update_quantum_job_status(namespace, name, success = True, error_message = None):
    """
    Update Quantum Job Status.
        - updates results, JobStatus and error message (if any) 
    
    :param namespace: Namespace of QuantumJob CR
    :param name: Name of QuantumJob CR
    :param result_b64: Base64 encode result
    :param success: Status of Job
    :param error_message: Error message
    """
    try:
        api  = client.CustomObjectsApi()

        status_body = {
            "status": {
                "errorMessage": error_message if not success else "",
            } 
        }

        api.patch_namespaced_custom_object_status(
            group = "aerjob.nav.io",
            version= "v2",
            namespace= namespace,
            plural = "quantumaerjobs",
            name = name,
            body = status_body
        )
        print(f"✅ Updated QuantumAerJob {name}")
    except Exception as e:
        print(f"❌ Status Update Failed: {e}")
        raise

def main():
    """
    Main execution flow
    """

    print("="*60) 
    print("Quantum Simulator Job Starting")
    print("="*60) 

    try:
        load_kube_config()

        redis_client = init_redis_client()
        # Get environment variables
        config_vars = get_env_vars()
        print(f"📋 Job ID: {config_vars['job_id']}")
        print(f"📋 Backend: {config_vars['backend_name']}")
        print(f"📋 Shots: {config_vars['shots']}")
        # print(f"📋 Target CR: {config_vars['quantum_job_namespace']}/{config_vars['quantum_job_name']}")

        circuit_key = f"t_circuit:{config_vars['job_id']}"
        print(f"Fetching Circuit from Redis: {circuit_key}")

        # Validate
        circuits_b64 = redis_client.get(circuit_key)
        if not circuits_b64:
            raise ValueError(f"Circuit not found in databse for key: {circuit_key}")

        # if not config_vars["circuits"]:
        #     raise ValueError("CIRCUITS environment variable is required.")
        if not config_vars["quantum_job_name"]:
            raise ValueError("QUANTUM_JOB_NAME environment variable is required.")
        if not config_vars["job_id"]:
            raise ValueError("Job_ID environment variable is required.")
        

        # Deserialize circuits
        circuits = deserialize_circuits(circuits_b64)

        # Run simulation
        results = run_simulation(
            circuits,
            config_vars['shots'],
            config_vars['backend_name']
        )

        # Serialize result
        result_b64 = serialize_results(results=results)
        print(f"Result Size: {len(result_b64)} bytes (base64)")

        # Update QuantumJob CR
        update_quantum_job_status(
            config_vars['quantum_job_namespace'], 
            config_vars['quantum_job_name'], 
            result_b64, 
            success= True, 
            error_message=None
        )

        print("="*60)
        print("✅ Job completed successfully")
        print("=" * 60)
        sys.exit(0) # pod phase marked as completed.

    except Exception as e:
        error_msg = f"{str(e)}"
        print("=" * 60)
        print(f"❌ Job failed: {e}")
        print("=" * 60)
        print(traceback.format_exc())

        # try to update CR with failure status
        try:
            config_vars = get_env_vars()
            if config_vars["quantum_job_name"]:
                update_quantum_job_status(
                    config_vars["quantum_job_namespace"], 
                    config_vars["quantum_job_name"],
                    "",
                    success=False,
                    error_message= error_msg[:1000] # Limit error
                )
        except:
            print("⚠️ Could not update CR with failure status")

        sys.exit(1) # pod phase marked as failed.

if __name__ == "__main__" :

    main()