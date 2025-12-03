***Create a KIND cluster***

```shell
kind create cluster --name <name-of-cluster> --config k8s/kind-config.yaml
```
I chose the name of KIND cluster as `qc-cluster`. 

***Create docker-images for pods***
```shell
# worker pod
docker build -t worker/Dockerfile.worker -f qiskit-worker:v2 .

# simulator pod + service
docker build -f simulator_service/Dockerfile.simulator -t aer-simulator:v2 .

# transpiler pod
docker build -t transpiler_service/Dockerfile.transpiler -f transpiler:v2 .
```

***Load docker-images to pods***
```shell
# worker pod
kind load docker-image qiskit-worker:v2 --name qc-cluster

# simulator pod + service
kind load docker-image aer-simulator:v2 --name qc-cluster

# transpiler pod + service
kind load docker-image transpiler:v2 --name qc-cluster

```

***Deploy PODS and Services***
```shell
# worker pod
kubectl apply -f k8s/worker-pod.yaml   

# simulator pod + service
kubectl apply -f k8s/simulator-deployment.yaml 

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
 ┌─────────────────────────────────────────────────────────────────────┐ 
 │                    Kubernetes Cluster (qc-cluster)                  │ 
 │                                                                     │ 
 │  ┌───────────────────────────────────────────────────────────────┐  │ 
 │  │                     Control Plane                             │  │ 
 │  │        - API Server                                           │  │ 
 │  │        - Scheduler (decides where pods run)                   │  │ 
 │  │        - etcd (stores cluster state)                          │  │ 
 │  └────────────────────────────────┬──────────────────────────────┘  │ 
 │                                   │                                 │ 
 │              ┌────────────────────┼──────────────────────────┐      │ 
 │              │                    │                          │      │ 
 │      ┌───────▼────────┐  ┌────────▼────────┐   ┌─────────────▼───┐  │ 
 │      │   Node 1/2     │  │    Node 1/2     │   │   Node 1/2      │  │ 
 │      │                │  │                 │   │                 │  │ 
 │      │ ┌────────────┐ │  │ ┌─────────────┐ │   │ ┌─────────────┐ │  │ 
 │      │ │worker-pod  │ │  │ │ transpiler  │ │   │ │ simulator   │ │  │ 
 │      │ │            │ │  │ │ -pod        │ │   │ │  -pod       │ │  │ 
 │      │ │Runs user   │ │  │ │             │ │   │ │             │ │  │ 
 │      │ │code        │ │  │ │ Transpiles  │ │   │ │  Simulates  │ │  │ 
 │      │ └──────┬─────┘ │  │ └─────▲─────┬─┘ │   │ └────────▲────┘ │  │ 
 │      └────────┼───────┘  └───────┼─────┼───┘   └──────────┼──────┘  │ 
 │               │                  │     │                  │         │ 
 │               │                  │     │                  │         │ 
 │               │  ┌───────────────┴────┐│                  │         │ 
 │               └─►│transpiler-service  ││                  │         │ 
 │                  │:5002 (ClusterIP)   ││                  │         │ 
 │                  └──▲─────────────────┘│                  │         │ 
 │                     │                  │                  │         │ 
 │                     │               ┌──▼─────────────────┐│         │ 
 │                     │               │simulator-service   ││         │ 
 │              injects secret         │:5001 (ClusterIP)   ├┘         │ 
 │                     │               └────────▲───────────┘          │ 
 │                     │                        │                      │ 
 │                  ┌──┴─────────────────┐ injects secret              │ 
 │                  │Secret:             │      │                      │ 
 │                  │ibm-quantum-secret  ├──────┘                      │ 
 │                  │(IBM API Key)       │                             │ 
 │                  └────────────────────┘                             │ 
 └─────────────────────────────────────────────────────────────────────┘ 

```