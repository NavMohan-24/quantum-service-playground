from qiskit import QuantumCircuit, transpile, qpy
from qiskit_aer import AerSimulator
from kubernetes import client, config
import base64, io

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

simulator = AerSimulator()
transpiled_qc = transpile(qc, simulator)

with io.BytesIO() as f:
    qpy.dump([transpiled_qc], f)
    circuits_b64 = base64.b64encode(f.getvalue()).decode()

config.load_kube_config()
api = client.CustomObjectsApi()

job = {
    "apiVersion" : "aerjob.nav.io/v2",
    "kind" : "QuantumAerJob",
    "metadata" : {"name" : "real-test-circuit"},
    "spec" : {
        "jobID": "real-test-001",
        "circuits" : circuits_b64,
        "simulatorImage": "aer-simulator:v3",
        "shots" : 1024,
        "backendName": "aer-simulator"

    }
}

api.create_namespaced_custom_object(
    group = "aerjob.nav.io",
    version = "v2",
    namespace="default",
    plural="quantumaerjobs",
    body=job
)

print("✅ Real circuit job created!")