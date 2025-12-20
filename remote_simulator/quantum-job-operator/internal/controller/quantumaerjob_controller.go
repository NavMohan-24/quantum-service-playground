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
	"sigs.k8s.io/controller-runtime/pkg/log"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	aerjobv2 "quantum/Aerjob/api/v2"
)

// QuantumAerJobReconciler reconciles a QuantumAerJob object
type QuantumAerJobReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=aerjob.nav.io,resources=quantumaerjobs,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=aerjob.nav.io,resources=quantumaerjobs/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=aerjob.nav.io,resources=quantumaerjobs/finalizers,verbs=update
// +kubebuilder:rbac:groups=core,resources=pods,verbs=get;list;watch;create;delete
// +kubebuilder:rbac:groups=core,resources=serviceaccounts,verbs=get;list;watch

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
func (r *QuantumAerJobReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	log := logf.FromContext(ctx)

	job := &aerjobv2.QuantumAerJob{}

	// Fetch job using Name.
	if err := r.Get(ctx,req.NamespacedName,job); err != nil{
		log.Info("Job is deleted since last reconcile")
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	log.Info("Reconciling Job", "name", job.Name, "phase", job.Status.JobStatus)
	
	// handle timeout of job
	if job.Status.StartTime != nil && job.Spec.Timeout > 0 {

		elapsed := time.Since(job.Status.StartTime.Time)
		timeout := time.Duration(job.Spec.Timeout)*time.Second

		if elapsed > timeout && job.Status.JobStatus != aerjobv2.Completed && 
			job.Status.JobStatus != aerjobv2.Failed {
				log.Info("Job timeout exceeded", "elapsed", elapsed, "timeout", timeout)
				return r.handleTimeout(ctx, job)
		}
	}

	switch job.Status.JobStatus{

		case "":
			return r.handleNewJob(ctx, job)
		
		case aerjobv2.Pending:
			return r.handlePendingJob(ctx,job)
		
		case aerjobv2.Progress:
			return r.handleRunningJob(ctx, job)
		
		case aerjobv2.Completed:
			return r.handleCompletedJob(ctx, job)
		
		case aerjobv2.Failed:
			return r.handleFailedJob(ctx, job)
			
	}
	return ctrl.Result{}, nil
}

func (r* QuantumAerJobReconciler) createSimulatorPod(ctx context.Context, job *aerjobv2.QuantumAerJob) (error){
	
	log := logf.FromContext(ctx)
	podName := fmt.Sprintf("%s-sim-%d-%d", job.Name, job.Status.Retries, time.Now().Unix())

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
				Env : []v1.EnvVar{
					{Name: "CIRCUITS", Value: job.Spec.Circuits},
					{Name: "SHOTS", Value: fmt.Sprintf("%d", job.Spec.Shots)},
					{Name: "BACKEND_NAME", Value: job.Spec.BackendName},
					{Name: "JOB_ID", Value: job.Spec.JobID},
					{Name: "QUANTUM_JOB_NAME", Value: job.Name},
					{Name: "QUANTUM_JOB_NAMESPACE", Value: job.Namespace},
					},
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

	if err:= r.Create(ctx, pod); err != nil{
		log.Info("Failed to create simulator pod", "podName", podName)
		return err
	}

	job.Status.PodName = podName
	return  r.Status().Update(ctx, job)
}

func (r* QuantumAerJobReconciler) getForPod(ctx context.Context, job *aerjobv2.QuantumAerJob)(pod *v1.Pod, err error){

	log := logf.FromContext(ctx)
	// fetches pod using name
	if job.Status.PodName != "" {
		var pod v1.Pod
		err := r.Get(ctx, types.NamespacedName{
			Name:      job.Status.PodName,
			Namespace: job.Namespace,
		}, &pod)

		if err != nil{
			log.Info("Failed to fetch simulator pod", "podName",job.Status.PodName)
			return nil, err
		}
		log.Info("Sucessfully fetched the simulator pod", "podName",job.Status.PodName)
		return &pod, err
	}

	return nil, errors.NewNotFound(v1.Resource("pod"), "")
}

func (r* QuantumAerJobReconciler) handleNewJob(ctx context.Context, job *aerjobv2.QuantumAerJob)(ctrl.Result, error){

	log := logf.FromContext(ctx)
	log.Info("Handling a new job", "job name", job.Name)

	job.Status.JobStatus = aerjobv2.Pending
	now := metav1.Now()
	job.Status.StartTime = &now
	job.Status.Retries = 0 // initialize retries

	if err := r.Status().Update(ctx,job); err != nil{
		return ctrl.Result{}, err
	}
	log.Info("Set job status to Pending")
	return ctrl.Result{Requeue: true}, nil
}

func (r* QuantumAerJobReconciler) handlePendingJob(ctx context.Context, job *aerjobv2.QuantumAerJob)(ctrl.Result, error){

	log := logf.FromContext(ctx, job)
	log.Info("Handling Pending Job", "job name", job.Name)

	_,err := r.getForPod(ctx, job)

	// if pod is not found create the pod
	if err != nil && errors.IsNotFound(err){
		if err := r.createSimulatorPod(ctx,job); err != nil{
			return ctrl.Result{},err
		}
		return ctrl.Result{}, err
	}
	// set the job status as In progress
	job.Status.JobStatus = aerjobv2.Progress
	if err := r.Status().Update(ctx, job); err != nil {
		return ctrl.Result{}, err
	}

	log.Info("Pod exists, transitioning to Progress")
	return ctrl.Result{RequeueAfter: 5*time.Second}, nil
}

func (r* QuantumAerJobReconciler) handleRunningJob(ctx context.Context, job *aerjobv2.QuantumAerJob)(ctrl.Result, error){

	log := logf.FromContext(ctx)
	pod, err := r.getForPod(ctx, job)

	if err != nil && errors.IsNotFound(err){
		job.Status.JobStatus = aerjobv2.Pending
		job.Status.PodName = "" // Clear pod name
		if err := r.Status().Update(ctx, job); err != nil {
			return ctrl.Result{}, err
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
					return ctrl.Result{}, err
				}

				job.Status.Retries++
				job.Status.JobStatus = aerjobv2.Pending
				job.Status.PodName = "" // Clear pod name for new pod
				if err := r.Status().Update(ctx,job); err != nil{
					return ctrl.Result{}, err
				}
				return ctrl.Result{RequeueAfter: 10*time.Second}, nil
			} else {
				log.Info("Max retries exceeded, marking job as Failed")
				job.Status.JobStatus = aerjobv2.Failed
				now := metav1.Now()
				job.Status.CompletionTime = &now
				if err := r.Status().Update(ctx,job); err != nil{
						return ctrl.Result{}, err
					}
				return ctrl.Result{RequeueAfter: 60*time.Second}, nil
			}	
		
		case v1.PodSucceeded :
			now := metav1.Now()
			job.Status.CompletionTime = &now
			log.Info("Pod suceeded,marking job as Completed")
			job.Status.JobStatus = aerjobv2.Failed

			if err := r.Status().Update(ctx,job); err != nil{
					return ctrl.Result{}, err
				}
			return ctrl.Result{RequeueAfter: 60*time.Second}, nil
			
		case v1.PodPending, v1.PodRunning :
			return ctrl.Result{RequeueAfter: 10 * time.Second}, nil
	}

	return ctrl.Result{}, nil
}

func (r *QuantumAerJobReconciler) handleTerminalJob(ctx context.Context, job *aerjobv2.QuantumAerJob)(ctrl.Result, error){

	log := logf.FromContext(ctx)
	pod, err := r.getForPod(ctx, job)

	if err != nil && errors.IsNotFound(err){
		job.Status.JobStatus = aerjobv2.Pending
		job.Status.PodName = "" // Clear pod name
		if err := r.Status().Update(ctx, job); err != nil {
			return ctrl.Result{}, err
		}
		log.Info("Transitioning back to Pending")
		return ctrl.Result{Requeue: true}, nil
	}
	if err != nil {
		return ctrl.Result{}, err
	}

	if job.Status.JobStatus == aerjobv2.Completed || job.Status.JobStatus == aerjobv2.Failed {

		log.Info("Job in terminal state, cleaning up the pods")
		if err := r.Delete(ctx, pod); err != nil && !errors.IsNotFound(err) {
			return ctrl.Result{}, err
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
				return ctrl.Result{}, err
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
	// job is not in terminal state thus requeue
	return ctrl.Result{Requeue: true}, nil	
}


// SetupWithManager sets up the controller with the Manager.
func (r *QuantumAerJobReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&aerjobv2.QuantumAerJob{}).
		Named("quantumaerjob").
		Complete(r)
}
