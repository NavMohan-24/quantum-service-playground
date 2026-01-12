import io
import base64
import json
import os
import sys
import uuid
import time
import traceback

from flask import Flask, request, Response, jsonify
from qiskit import QuantumCircuit, generate_preset_pass_manager,qpy
from qiskit_ibm_runtime.utils import RuntimeEncoder, RuntimeDecoder
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_aer import AerSimulator
from kubernetes import client, config
from utils.redisDB import RedisDB


##=============INTIALISING REDIS=================

app = Flask(__name__)

IBM_API_KEY = os.getenv('IBM_API_KEY')
IBM_INSTANCE = os.getenv('IBM_INSTANCE')
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")

SIMULATOR_IMAGE = os.getenv('SIMULATOR_IMAGE', 'aer-simulator:v3')
K8S_NAMESPACE = os.getenv('K8S_NAMESPACE', 'default')
JOB_TIMEOUT = int(os.getenv('JOB_TIMEOUT', '600'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
DEFAULT_TTL = int(os.getenv('DEFAULT_TTL_SECONDS', '300'))

service = None
def init_ibm_service():
    global service
    if service is not None:  
        return
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


# Initialize on startup
init_ibm_service()
load_kube_config()
redis_client = RedisDB(redis_host=REDIS_HOST, redis_port=REDIS_PORT)
k8s_api = client.CustomObjectsApi()
print("Initialized Transpiler Service : ✅ ")


##========== HELPER FUNCTIONS =======================
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

def create_quantum_job(circuits_b64, shots, backend_name, job_ID, resources = None):
    """
    Creates a QuantumJob Custom Resource in Kuberenets
    
    :param circuits_b64: base64 encoded circuit.
    :param shots: Number of shots for Sampling.
    :param backend_name: Name of the backend.
    :param job_name: Name of the job.
    :param resources: Resource specified.
    """
    # Generate the ID

    if not job_ID:
        job_ID = uuid.uuid4().hex[:16]

    job_name = f"qjob-{job_ID}"

    redis_client.create_job_data(job_id=job_ID,circuit=circuits_b64)
    print(f"📝 Stored circuit in DB: {job_ID}")

    quantum_job_spec = {
        "backendName": backend_name,
        "shots" : shots,
        "simulatorImage": SIMULATOR_IMAGE,
        "jobID" : job_ID,
        "maxRetries": MAX_RETRIES,
        "timeOut" : JOB_TIMEOUT,
        "ttlSecondsAfterFinished" : DEFAULT_TTL
    }

    if resources:
        quantum_job_spec['resources'] = resources
    
    quantum_job = {
        "apiVersion" : "aerjob.nav.io/v3",
        "kind" : "QuantumAerJob",
        "metadata": {
            "name" : job_name,
            "namespace" : K8S_NAMESPACE,
            "labels" : {
                "managed-by" : "transpiler-service",
                "job-id": job_ID
            }

        },
        "spec": quantum_job_spec
    }

    print(f"📝 Creating QuantumJob CR: {job_name}")

    try:
        k8s_api.create_namespaced_custom_object(
            group = "aerjob.nav.io",
            version = "v3",
            namespace=K8S_NAMESPACE,
            plural = "quantumaerjobs",
            body = quantum_job)

        print(f"✅ QuantumJob {job_name} created")
        return job_name, job_ID
    
    except Exception as e:
        print(f"❌ Failed to create QuantumJob: {e}")
        raise


def get_quantum_job_status(job_ID):
    """
    Return the status of a job
    
    :param job_name: Name of the job whose status needs to be checked.
    """    
    job_name = f"qjob-{job_ID}"
    try:
        job = k8s_api.get_namespaced_custom_object(
            group = "aerjob.nav.io",
            version = "v3",
            namespace= K8S_NAMESPACE,
            plural= "quantumaerjobs",
            name = job_name
        )

        return job.get("status", {})
    
    except Exception as e:
        print(f"❌ Failed to get job status: {e}")
        return {}
    

def delete_quantum_job(job_name):

    """
    Delete QuantumJob CR
    
    :param job_name: Name of the job
    """

    try:
        k8s_api.delete_namespaced_custom_object(
            group = "aerjob.nav.io",
            version = "v2",
            namespace= K8S_NAMESPACE,
            name = job_name,
            plural= "quantumaerjobs"
        )
        print(f"🗑️ job {job_name} has been deleted.")
    except Exception as e:
        print(f"⚠️ failed to delete the job {job_name}: {e}")
    
##=========== ENDPOINTS =============================
@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "transpiler",
        "ibm_available": service is not None
    })

@app.route("/transpile", methods=["POST"])
def transpile():

    try:
        data = request.get_json()

        # decode the circuit
        circuits_b64 = data.get('circuits_qpy')
        shots = data.get("shots", 1024)
        backend_name = data.get("backend_name", "aer-simulator")
        job_id = data.get("job_id", None)
        resources = data.get('resources', None)

        if not circuits_b64:
            return jsonify({"Transpiler error": "No circuits provided"}), 400
        
        circuits = deserialize_circuits(circuits_b64)
    
        
        if backend_name == "aer-simulator" or not service:
            target = AerSimulator().target    
        else:
            target = service.backend(name=backend_name).target
        
        pm = generate_preset_pass_manager(optimization_level=3, target=target)
        isa_circuits = pm.run(circuits)

        # serialize the circuit
        with io.BytesIO() as fptr:
            qpy.dump(isa_circuits, fptr)
            isa_circuit_bytes = fptr.getvalue()
            isa_circuit_b64 = base64.b64encode(isa_circuit_bytes).decode("utf-8")

        job_name, job_id = create_quantum_job(isa_circuit_b64, shots, backend_name, job_id, resources)

        return jsonify({
            "status" : "accepted",
            "job_id" :  job_id, 
            "error" : "",
            "message": f"Job submitted. Poll /job/{job_id}/status for updates"
             }), 202  

    except Exception as e:
        return jsonify({
            "status": "failed",
            "job_id": "",
            "error": str(e),
            "message": traceback.format_exc()
        }), 500
        
    
    
@app.route("/job/<job_ID>/status", methods=["GET"])
def get_job_status_endpoint(job_ID):
    """
    Get the status of a specific QuantumJob
    
    Useful for async polling if needed
    """
    try:
        status = get_quantum_job_status(job_ID)

        # function returns empty, JOB doesnot exists
        if not status:
            return jsonify({
                "error": f"Job {job_ID} is not Found",
                "details" : ""
            }), 404
        
        # request successful
        return jsonify(status), 200
    
    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details" : str(e)}), 500


@app.route("/job/<job_ID>/result", methods=["GET"])
def get_job_result_endpoint(job_ID):
    """
    Get the result of a completed QuantumJob
    """
    try:
        status = get_quantum_job_status(job_ID)
        
        if status.get("jobStatus") != "completed":
            return jsonify({
                "error": "Job not completed",
                "status": status.get("state", "unknown")
            }), 400
        
        # result_b64 = status.get("result", "")
        job_data = redis_client.get_job_data(job_id=job_ID)
        return jsonify({
            "status": "success",
            "result": job_data.get("results",None)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 404

##==========MAIN FUNCTION=========================
if __name__ == '__main__':
    print("🚀 Starting Transpiler Service on port 5002...")
    app.run(host='0.0.0.0', port=5002)

