from qiskit import QuantumCircuit
from remote_aer_backend import RemoteAerBackend

# constructing circuit
qc = QuantumCircuit(2,2)
qc.h(0)
qc.cx(0,1)
qc.barrier()
qc.measure_all()

# executing it in remote-simulator

backend = RemoteAerBackend(name="ibm_fez")
job = backend.run(qc, shots=4096)
result = job.result()

print("Backend results:", result[0].data.meas.get_counts())