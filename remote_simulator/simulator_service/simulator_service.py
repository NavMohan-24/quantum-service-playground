import json
import io
import base64
import os

from flask import Flask, request, Response, jsonify
from qiskit import QuantumCircuit, transpile,qpy
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
from qiskit_ibm_runtime.utils import RuntimeEncoder, RuntimeDecoder


# set up a webserver instance 
app = Flask(__name__)  #__name__ denotes module name

IBM_API_KEY = os.getenv('IBM_API_KEY')
IBM_INSTANCE = os.getenv('IBM_INSTANCE')  

print("API KEY :",repr(IBM_API_KEY))
print("Instance :",repr(IBM_INSTANCE))


# Initialize service and cache backends at startup
service = None
backend_cache = {}

def init_ibm_service():
    global service
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

# Initialize on startup
init_ibm_service()


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service" : "aer-simulator"})

@app.route("/execute", methods=['POST']) # only accepts POST method.
def execute():

    data = request.get_json()

    # decode the circuit
    circuits_b64 = data.get('isa_circuits_b64')
    shots = data.get("shots", 1024)
    backend_name = data.get("backend_name", "ibm_torino")


    if not circuits_b64:
        return jsonify({"error": "No circuits provided"}), 400
    
    service = QiskitRuntimeService(
    channel="ibm_quantum_platform",
    token = IBM_API_KEY,
    instance= IBM_INSTANCE)

    backend = service.backend(name = backend_name)
    simulator = AerSimulator.from_backend(backend=backend)
    sampler = SamplerV2(mode=simulator)

    try:
        
        # deserialize circuits
        circuits_bytes = base64.b64decode(circuits_b64)
        with io.BytesIO(circuits_bytes) as fptr:
            circuits = qpy.load(fptr)

        print(f"Received {len(circuits)} circuit(s) for execution with {shots} shots")
        
        # # transpile
        # print("Transpiling circuits...")
        # tqc = transpile(circuits, simulator)
        
        # run and retrieve a job
        print(f"Running simulation with {shots} shots...")
        job = sampler.run(pubs=circuits, shots=shots)
        result = job.result()

        # Serialize result using RuntimeEncoder, then base64 encode
        result_json = json.dumps(result, cls=RuntimeEncoder)
        result_bytes = result_json.encode('utf-8')
        result_b64 = base64.b64encode(result_bytes).decode('utf-8')

        return jsonify({
            "status": "success",
            "result": result_b64
        })
    
    except Exception as e:
        import traceback
        print(f"Error during execution: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    print("Starting AerSimulator Service on port 5001...")
    app.run(host='0.0.0.0', port=5001)

























    