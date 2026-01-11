/*
Copyright 2025.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package controller

import (
	"context"
	"fmt"
	"time"

	v1 "k8s.io/api/core/v1"
	errors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"

	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	aerjob "quantum/Aerjob/api/v3"
)

// Requeue delay constants for reconciliation backoff
const (
    FastRequeueDelay    = 5 * time.Second // for polling state change
    DefaultRequeueDelay = 10 * time.Second // for handling errors
    SlowRequeueDelay    = 60 * time.Second // clean-up
)

// QuantumAerJobReconciler reconciles a QuantumAerJob object
type QuantumAerJobReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// kubebuilder markers to give necessary rbac premission to controller
// give access to read & updaate quantumaerjobs resources.
// give access to read & update pods/service accounts

// +kubebuilder:rbac:groups=aerjob.nav.io,resources=quantumaerjobs,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=aerjob.nav.io,resources=quantumaerjobs/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=aerjob.nav.io,resources=quantumaerjobs/finalizers,verbs=update
// +kubebuilder:rbac:groups=core,resources=pods,verbs=get;list;watch;create;delete
// +kubebuilder:rbac:groups=core,resources=serviceaccounts,verbs=get;list;watch

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
func (r *QuantumAerJobReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := logf.FromContext(ctx)

	job := &aerjob.QuantumAerJob{}

	// Fetch job using Name.
	if err := r.Get(ctx,req.NamespacedName,job); err != nil{
		log.Info("Job is deleted since last reconcile")
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	log.Info("Reconciling Job", "name", job.Name, "phase", job.Status.JobStatus)
	
	// handle timeout of job
	if job.Status.StartTime != nil && job.Spec.TimeOut > 0 {

		elapsed := time.Since(job.Status.StartTime.Time)
		timeout := time.Duration(job.Spec.TimeOut)*time.Second

		if elapsed > timeout && job.Status.JobStatus != aerjob.Completed && 
			job.Status.JobStatus != aerjob.Failed {
				log.Info("Job timeout exceeded", "elapsed", elapsed, "timeout", timeout)
				// Mark as failed
				job.Status.JobStatus = aerjob.Failed
				job.Status.ErrorMessage = fmt.Sprintf("Job exceeded timeout of %d seconds", job.Spec.TimeOut)
				now := metav1.Now()
				job.Status.CompletionTime = &now

				if err := r.Status().Update(ctx, job); err != nil {
					return ctrl.Result{}, err
				}
				// Let handleTerminalJob clean up
				return ctrl.Result{Requeue: true}, nil	
		}
	}

	switch job.Status.JobStatus{

		case "":
			return r.handleNewJob(ctx, job)
		
		case aerjob.Pending:
			return r.handlePendingJob(ctx,job)
		
		case aerjob.Progress:
			return r.handleRunningJob(ctx, job)
		
		case aerjob.Completed, aerjob.Failed:
			return r.handleTerminalJob(ctx, job)
			
	}
	return ctrl.Result{}, nil
}

func (r *QuantumAerJobReconciler) validateServiceAccount(ctx context.Context, namespace, saName string) error {
    sa := &v1.ServiceAccount{}
    err := r.Get(ctx, types.NamespacedName{
        Name:      saName,
        Namespace: namespace,
    }, sa)
    
    if errors.IsNotFound(err) {
        return fmt.Errorf("ServiceAccount %s not found in namespace %s", saName, namespace)
    }
    return err
}

func (r* QuantumAerJobReconciler) createSimulatorPod(ctx context.Context, job *aerjob.QuantumAerJob) (error){
	
	log := logf.FromContext(ctx)
	podName := fmt.Sprintf("%s-sim-%d", job.Name, job.Status.Retries)

	// Validate ServiceAccount exists
    if err := r.validateServiceAccount(ctx, job.Namespace, "quantum-simulator-sa"); err != nil {
        log.Error(err, "ServiceAccount validation failed, pod couldn't be created")
        return err
    }

	// redisSvc := &v1.Service{}
	// if err:= r.Get(ctx, types.NamespacedName{Name: "redis-service", Namespace: job.Namespace}, redisSvc); err != nil{
	// 	log.Error(err, "Redis service couldn't be found, pod couldn't be created")
    //     return err
	// }

	envVar := []v1.EnvVar{
		{Name: "JOB_ID" , Value: job.Spec.JobID},
		{Name: "BACKEND_NAME", Value: job.Spec.BackendName},
		{Name: "SHOTS", Value: fmt.Sprintf("%d",job.Spec.Shots)},
		{Name: "SIMULATOR_IMAGE", Value: job.Spec.SimulatorImage},
		{Name: "QUANTUM_JOB_NAME", Value: job.Name},
		{Name: "QUANTUM_JOB_NAMESPACE",Value: job.Namespace},
		{Name: "IBM_API_KEY", ValueFrom: &v1.EnvVarSource{
			SecretKeyRef: &v1.SecretKeySelector{
				LocalObjectReference: v1.LocalObjectReference{
					Name: "ibm-quantum-secret",
					}, 
					Key: "api-key",
				},
			},
		},
		{Name: "IBM_INSTANCE", ValueFrom: &v1.EnvVarSource{
			SecretKeyRef: &v1.SecretKeySelector{
				LocalObjectReference: v1.LocalObjectReference{
					Name: "ibm-quantum-secret",
					}, 
					Key: "instance",
				},
			},
		},
		{Name: "REDIS_HOST", ValueFrom: &v1.EnvVarSource{
			ConfigMapKeyRef: &v1.ConfigMapKeySelector{
				LocalObjectReference: v1.LocalObjectReference{
					Name: "redis-config",
					},
					Key : "host",
				},
			},
		},
		{Name: "REDIS_PORT", ValueFrom: &v1.EnvVarSource{
			ConfigMapKeyRef: &v1.ConfigMapKeySelector{
				LocalObjectReference: v1.LocalObjectReference{
					Name: "redis-config",
					},
					Key : "port",
				},
			},
		},
	}


	pod := &v1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name : podName,
			Namespace: job.Namespace,
			Labels: map[string]string{
				"app":  "quantum-simulator",
				"quantum-job": job.Name,
			},
		},

		Spec: v1.PodSpec{
			RestartPolicy: v1.RestartPolicyNever,
			ServiceAccountName: "quantum-simulator-sa",
			Containers: []v1.Container{
				{
				Name : "aer-simulator",
				Image : job.Spec.SimulatorImage,
				Env : envVar,
				Resources: v1.ResourceRequirements{
					Requests: v1.ResourceList{
						v1.ResourceCPU: resource.MustParse("1"),
						v1.ResourceMemory: resource.MustParse("512Mi"),
						},
					Limits: v1.ResourceList{
						v1.ResourceCPU: resource.MustParse("2"),
						v1.ResourceMemory: resource.MustParse("2Gi"),
						},
					},
				},	
			},
		},
	}


	// set owner reference
	if err := ctrl.SetControllerReference(job, pod, r.Scheme); err != nil{
		return err
	}

	log.Info("Creating simulator pod", "podName", podName)
	
	err:= r.Create(ctx, pod);
	if err != nil{
		if errors.IsAlreadyExists(err){
			log.Info("Pod already exists, skipping creation", "podName", podName)
			// Do not exit if it is an already exists error.
		}else{
			log.Info("Failed to create simulator pod", "podName", podName)
			return err
		}
	}
    
	if job.Status.PodName != podName{
		job.Status.PodName = podName
		return  r.Status().Update(ctx, job)
	}
	return nil
}

func (r* QuantumAerJobReconciler) getForPod(ctx context.Context, job *aerjob.QuantumAerJob) (*v1.Pod, error) {
    log := logf.FromContext(ctx)
    
    if job.Status.PodName == "" {
        return nil, errors.NewNotFound(v1.Resource("pod"), "")
    }
    
    pod := &v1.Pod{}
    err := r.Get(ctx, types.NamespacedName{ 
        Name:      job.Status.PodName,
        Namespace: job.Namespace,
    }, pod)
    
    if err != nil {
        log.Info("Failed to fetch simulator pod", "podName", job.Status.PodName)
        return nil, err
    }
    
    log.Info("Successfully fetched the simulator pod", "podName", job.Status.PodName)
    return pod, nil
}

func (r* QuantumAerJobReconciler) handleNewJob(ctx context.Context, job *aerjob.QuantumAerJob)(ctrl.Result, error){

	log := logf.FromContext(ctx)
	log.Info("Handling a new job", "job name", job.Name)

	job.Status.JobStatus = aerjob.Pending
	now := metav1.Now()
	job.Status.StartTime = &now
	job.Status.Retries = 0 // initialize retries

	if err := r.Status().Update(ctx,job); err != nil{
		return ctrl.Result{RequeueAfter: DefaultRequeueDelay}, err
	}
	log.Info("Set job status to Pending")
	return ctrl.Result{Requeue: true}, nil
}

func (r* QuantumAerJobReconciler) handlePendingJob(ctx context.Context, job *aerjob.QuantumAerJob)(ctrl.Result, error){

	log := logf.FromContext(ctx)
	log.Info("Handling Pending Job", "job name", job.Name)

	_,err := r.getForPod(ctx, job)

	// if pod is not found create the pod
	if err != nil && errors.IsNotFound(err){
		if err2 := r.createSimulatorPod(ctx,job); err2 != nil{
			return ctrl.Result{RequeueAfter: DefaultRequeueDelay},err2
		}
		return ctrl.Result{Requeue:true}, nil
	}
	// set the job status as In progress
	job.Status.JobStatus = aerjob.Progress
	if err := r.Status().Update(ctx, job); err != nil {
		return ctrl.Result{RequeueAfter: DefaultRequeueDelay}, err
	}

	log.Info("Pod exists, transitioning to Progress")
	return ctrl.Result{Requeue: true}, nil
}

func (r* QuantumAerJobReconciler) handleRunningJob(ctx context.Context, job *aerjob.QuantumAerJob)(ctrl.Result, error){

	log := logf.FromContext(ctx)
	pod, err := r.getForPod(ctx, job)

	if err != nil && errors.IsNotFound(err){
		job.Status.JobStatus = aerjob.Pending
		job.Status.PodName = "" // Clear pod name
		if err := r.Status().Update(ctx, job); err != nil {
			return ctrl.Result{RequeueAfter: DefaultRequeueDelay}, err
		}
		log.Info("Transitioning back to Pending")
		return ctrl.Result{Requeue: true}, nil
	}
	if err != nil {
		return ctrl.Result{}, err
	}

	log.Info("Handling Running Job", "Job Name", job.Name)
	switch pod.Status.Phase{
		
		case v1.PodFailed :
			log.Info("Pod failed", "retries", job.Status.Retries, "maxRetries", job.Spec.MaxRetries)
			
			if job.Status.Retries < job.Spec.MaxRetries{

				// Delete failed pod
				if err := r.Delete(ctx, pod); err != nil && !errors.IsNotFound(err) {
					return ctrl.Result{RequeueAfter: DefaultRequeueDelay}, err
				}

				job.Status.Retries++
				job.Status.JobStatus = aerjob.Pending
				job.Status.PodName = "" // Clear pod name for new pod
				if err := r.Status().Update(ctx,job); err != nil{
					return ctrl.Result{RequeueAfter: DefaultRequeueDelay}, err
				}
				return ctrl.Result{RequeueAfter: FastRequeueDelay}, nil
			} else {
				log.Info("Max retries exceeded, marking job as Failed")
				job.Status.JobStatus = aerjob.Failed
				job.Status.ErrorMessage = "Job terminated due to consistend Pod failures"
				now := metav1.Now()
				job.Status.CompletionTime = &now
				if err := r.Status().Update(ctx,job); err != nil{
						return ctrl.Result{RequeueAfter: DefaultRequeueDelay}, err
					}
				return ctrl.Result{RequeueAfter: 60*time.Second}, nil
			}	
		
		case v1.PodSucceeded :
			now := metav1.Now()
			job.Status.CompletionTime = &now
			log.Info("Pod suceeded,marking job as Completed")
			job.Status.JobStatus = aerjob.Completed

			if err := r.Status().Update(ctx,job); err != nil{
					return ctrl.Result{RequeueAfter: DefaultRequeueDelay}, err
				}
			return ctrl.Result{RequeueAfter: SlowRequeueDelay}, nil
			
		case v1.PodPending, v1.PodRunning :
			return ctrl.Result{RequeueAfter: FastRequeueDelay}, nil
	}

	return ctrl.Result{}, nil
}

func (r *QuantumAerJobReconciler) handleTerminalJob(ctx context.Context, job *aerjob.QuantumAerJob)(ctrl.Result, error){

	log := logf.FromContext(ctx)

	if job.Status.JobStatus == aerjob.Completed || job.Status.JobStatus == aerjob.Failed {

		log.Info("Job in terminal state, cleaning up the pods")

		pod, err := r.getForPod(ctx, job)

		if err == nil{
			log.Info("Deleting pod","podName", pod.Name)
			if err := r.Delete(ctx, pod); err != nil && !errors.IsNotFound(err) {
			return ctrl.Result{RequeueAfter: DefaultRequeueDelay}, err
			}

		} else if errors.IsNotFound(err){
			// pod already gone, nothing to do
			log.Info("Pod Already deleted")
		} else {
			// other error
			return ctrl.Result{RequeueAfter: DefaultRequeueDelay},err
		}
		
		// Deleting the CR if it exceeds TTL
		if job.Spec.TTLSecondsAfterFinished != nil && job.Status.CompletionTime != nil{

			ttl := time.Duration(*job.Spec.TTLSecondsAfterFinished)*time.Second
			elapsed := time.Since(job.Status.CompletionTime.Time)

			if elapsed >= ttl {
				log.Info("TTL exceeded, deleting QuantumJob CR", 
					"name", job.Name, 
					"ttl", ttl, 
					"elapsed", elapsed)

				if err := r.Delete(ctx, job); err != nil {
					if errors.IsNotFound(err) {
						// Already deleted, nothing to do
						return ctrl.Result{}, nil
					}
					log.Error(err, "Failed to delete QuantumJob CR")
					return ctrl.Result{RequeueAfter: DefaultRequeueDelay}, err
				}
				log.Info("QuantumJob CR deleted successfully", "name", job.Name)
				return ctrl.Result{}, nil
			}
			// TTL not yet reached, schedule next check
			remaining := ttl - elapsed
			log.Info("TTL not reached, requeueing", 
				"remaining", remaining, 
				"nextCheck", time.Now().Add(remaining))
			
			return ctrl.Result{RequeueAfter: remaining}, nil
		}else{
			// No TTL set, job will remain indefinitely
			log.Info("No TTL set, job will be retained", "name", job.Name)
			return ctrl.Result{}, nil
		}
	
	}
	// Not in terminal state (shouldn't happen)
	log.Info("handleTerminalJob called but job not in terminal state", "status", job.Status.JobStatus)
	return ctrl.Result{}, nil
}



// SetupWithManager sets up the controller with the Manager.
func (r *QuantumAerJobReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&aerjob.QuantumAerJob{}).
		Owns(&v1.Pod{}).
		Named("quantumaerjob").
		Complete(r)
}
