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

package v3

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// EDIT THIS FILE!  THIS IS SCAFFOLDING FOR YOU TO OWN!
// NOTE: json tags are required.  Any new fields you add must have json tags for the fields to be serialized.

// QuantumAerJobSpec defines the desired state of QuantumAerJob
type QuantumAerJobSpec struct {
	
	// BackendName is the Qiskit Aer backend to use
	// +optional
	// +kubebuilder:default:=aer-simulator
	BackendName string `json:"backendName,omitempty"`

	// Shots is the number of times to run the circuit.
	// +optional
	// +kubebuilder:default:=1024
	// +kubebuilder:validation:Minimum:=1
	Shots int32 `json:"shots,omitempty"`
	
	// Circuits is a string representation of the quantum circuits to execute.
	// This should be a base64-encoded QPY serialized circuit.
	// +kubebuilder:validation:Required
	Circuits string `json:"circuits"`

	// SimulatorImage contains the image for simulator
	// +kubebuilder:validation:Required
	SimulatorImage string `json:"simulatorImage,omitempty"`

	// JobID is a unique identifier for this simulation job.
	// +optional
	JobID string `json:"jobID,omitempty"`

	// MaxRetries allowed if pod fails
	// +optional
	// +kubebuilder:default:=3
	MaxRetries int32 `json:"maxRetries,omitempty"`

	// Timeout for the simulation job in seconds
	// +optional
	// +kubebuilder:default:=600
	TimeOut int32 `json:"timeOut,omitempty"`
	
	// TTLSecondsAfterFinished limits the lifetime of a Job that has finished
	// execution (either Completed or Failed).
	// +optional
	// +kubebuilder:default:=300
	TTLSecondsAfterFinished *int32 `json:"ttlSecondsAfterFinished,omitempty"`

	// Resources defines the compute resources required for the simulator pod
	// +optional
	Resources ResourceRequirements `json:"resources,omitempty"`
	
}

// ResourceRequirements defines resource requests and limits
type ResourceRequirements struct {
	// Requests describes the minimum amount of compute resources required
	// +optional
	Requests ResourceList `json:"requests,omitempty"`
	
	// Limits describes the maximum amount of compute resources allowed
	// +optional
	Limits ResourceList `json:"limits,omitempty"`
}

// ResourceList is a set of (resource name, quantity) pairs
type ResourceList struct {
	// CPU in cores (e.g., "500m" for 0.5 cores)
	// +optional
	// +kubebuilder:default:="500m"
	CPU string `json:"cpu,omitempty"`
	
	// Memory in bytes (e.g., "512Mi")
	// +optional
	// +kubebuilder:default:="512Mi"
	Memory string `json:"memory,omitempty"`
}

type JobState string

const(
	Pending JobState = "pending"
	Progress JobState = "in progress"
	Completed JobState = "completed"
	Failed JobState = "failed"
)

// QuantumAerJobStatus defines the observed state of QuantumAerJob.
type QuantumAerJobStatus struct {
	
	// The status of each condition is one of True, False, or Unknown.
	// +listType=map
	// +listMapKey=type
	// +optional
	Conditions []metav1.Condition `json:"conditions,omitempty"`

	// JobStatus is the current state of the Job
	// +optional
	JobStatus JobState `json:"state,omitempty"`

	// Result is the base64-encoded execution result
	// +optional
	Result string `json:"result,omitempty"`

	// ErrorMessage contains error details if the job failed
	// +optional
	ErrorMessage string `json:"errorMessage,omitempty"`

	// Retries tracks the number of retry attempts
	// +optional
	// +kubebuilder:default:=0
	Retries int32 `json:"retries,omitempty"`
	
	// PodName is the name of the simulator pod
	// +optional
	PodName string `json:"podName,omitempty"`
	
	// StartTime is when the job started executing
	// +optional
	StartTime *metav1.Time `json:"startTime,omitempty"`
	
	// CompletionTime is when the job finished
	// +optional
	CompletionTime *metav1.Time `json:"completionTime,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status 
// +kubebuilder:printcolumn:name="State",type=string,JSONPath=`.status.state`
// +kubebuilder:printcolumn:name="Backend",type=string,JSONPath=`.spec.backendName`
// +kubebuilder:printcolumn:name="Retries",type=integer,JSONPath=`.status.retries`
// +kubebuilder:printcolumn:name="Age",type=date,JSONPath=`.metadata.creationTimestamp`

// Setting status of a subresource implies it could be accessed via quantumaerjob/status.
// QuantumAerJob is the Schema for the quantumaerjobs API
type QuantumAerJob struct {
	metav1.TypeMeta `json:",inline"`

	// metadata is a standard object metadata
	// +optional
	metav1.ObjectMeta `json:"metadata,omitzero"`

	// spec defines the desired state of QuantumAerJob
	// +required
	Spec QuantumAerJobSpec `json:"spec"`

	// status defines the observed state of QuantumAerJob
	// +optional
	Status QuantumAerJobStatus `json:"status,omitzero"`
}

// +kubebuilder:object:root=true

// QuantumAerJobList contains a list of QuantumAerJob
type QuantumAerJobList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitzero"`
	Items           []QuantumAerJob `json:"items"`
}

func init() {
	SchemeBuilder.Register(&QuantumAerJob{}, &QuantumAerJobList{})
}
