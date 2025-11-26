import json

from flask import Flask, request, Response, jsonify
from qiskit import QuantumCircuit, transpile,qpy
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.utils import RuntimeEncoder, RuntimeDecoder


import io
import base64

# set up a webserver instance 
app = Flask(__name__)  #__name__ denotes module name

# initialize the simulator   
print("Initializing AerSimulator...")
simulator = AerSimulator()
sampler = SamplerV2(mode=simulator)
print("AerSimulator initialized successfully")


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service" : "aer-simulator"})

@app.route("/execute", methods=['POST']) # only accepts POST method.
def execute():

    try:
        data = request.get_json()

        # decode the circuit
        circuits_b64 = data.get('circuits_qpy')
        shots = data.get("shots", 1024)
        # method = data.get("method", "automatic")


        if not circuits_b64:
            return jsonify({"error": "No circuits provided"}), 400
        
        # deserialize circuits
        circuits_bytes = base64.b64decode(circuits_b64)
        with io.BytesIO(circuits_bytes) as fptr:
            circuits = qpy.load(fptr)

        print(f"Received {len(circuits)} circuit(s) for execution with {shots} shots")
        
        # transpile
        print("Transpiling circuits...")
        tqc = transpile(circuits, simulator)
        
        # run and retrieve a job
        print(f"Running simulation with {shots} shots...")
        job = sampler.run(pubs=tqc, shots=shots)
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

























    