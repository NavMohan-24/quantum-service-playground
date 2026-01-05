***Create a KIND cluster***

```shell
kind create cluster --name <name-of-cluster> --config k8s/kind-config.yaml
```
I chose the name of KIND cluster as `qc-cluster`. 

***Create docker-images for pods***
```shell
# worker pod
docker build -f worker/Dockerfile.worker -t qiskit-worker:v3 .

# transpiler pod 
docker build -f transpiler_service/Dockerfile.transpiler -t transpiler:v3 .

# simulator pod
docker build -f simulator_service/Dockerfile.simulator -t aer-simulator:v3 .
```
***Deploy Quantum Job Operator***
```shell
cd quantum-job-operator
make generate
make manifests
make docker-build IMG=quantumjob-operator:v2
kind load docker-image quantumjob-operator:v2 --name qc-cluster
kubectl delete deployment quantum-job-operator-controller-manager -n quantum-job-operator-system
make deploy IMG=quantumjob-operator:v2
cd ..
```

***Load docker-images to pods***
```shell
# worker pod
kind load docker-image qiskit-worker:v3 --name qc-cluster

# transpiler pod + service
kind load docker-image transpiler:v3 --name qc-cluster

# worker pod 
kind load docker-image aer-simulator:v3 --name qc-cluster
```

***Deploy PODS, Secrets & Services***
```shell
# secrets
kubectl apply -f k8s/ibm-quantum-secret.yaml

# service accounts
kubectl apply -f k8s/simulator-rbac.yaml
kubectl apply -f k8s/transpiler-rbac.yaml

# worker pod
kubectl apply -f k8s/worker-pod.yaml   

# transpiler pod + service
kubectl apply -f k8s/transpiler-deployment.yaml
```

***Execute the test code***

```bash
# copy the test code to worker pod
kubectl cp test_job.py qiskit-worker-pod:/app/

# execute it
kubectl exec -it qiskit-worker-pod -- python worker.py test_job.py

```
<!-- ```
architecture
                                                         
   ┌─────────────────────────────────────────────────┐   
   │                  qc-cluster                     │   
   │                                                 │   
   │             ┌────────────────────┐              │   
   │             │   control-plane    │              │   
   │             └────────────────────┘              │   
   │                                                 │   
   │ ┌─────────────────┐       ┌───────────────────┐ │   
   │ │                 │       │                   │ │   
   │ │  worker-node-1/2│       │  worker-node-1/2  │ │   
   │ │                 │       │                   │ │   
   │ │ ┌─────────────┐ │       │  ┌──────────────┐ │ │   
   │ │ │             │ │       │  │              │ │ │   
   │ │ │ qiskit-     │ │       │  │ aer-         │ │ │   
   │ │ │ worker-pod  │ │       │  │ simulator-pod│ │ │   
   │ │ │             │ │       │  │              │ │ │   
   │ │ └──────────┬▲─┘ │       │  └─▲┌───────────┘ │ │   
   │ │       http ││   │       │    ││ kube-proxy  │ │   
   │ └────────────┼┼───┘       └────┼┼─────────────┘ │   
   │             ┌▼└────────────────┴▼─┐             │   
   │             │  simulator-service  |             |
   │             │   (Cluster IP)      |             |
   │             └─────────────────────┘             │   
   │                                                 │   
   │                                                 │   
   └─────────────────────────────────────────────────┘   

```                                                          -->
                                                         
```
┌──────────┐   HTTP    ┌─────────────┐   creates   ┌──────────────┐
│  Worker  ├──────────►│ Transpiler  ├────────────►│QuantumAerJob │
│   Pod    │           │   Service   │   (via API) │      CR      │
└──────────┘           └─────────────┘             └──────┬───────┘
      │                                                   │
      │                                               watches
      │                                                   │
      │                                            ┌──────▼-──────┐
      │                                            │   Operator   │
      │                                            │  (reconcile) │
      │                                            └───────┬──────┘
      │                                                    │creates
      │                                                    │
      │                  ┌─────────────────────────────────▼────┐
      │                  │      simulator-pod                   │
      │                  │      - runs simulation               │
      │                  │      - updates CR status             │
      │                  └──────────────────────────────────────┘
      │                                    │
      └────polls for result────────────────┘
           (via transpiler service)

```