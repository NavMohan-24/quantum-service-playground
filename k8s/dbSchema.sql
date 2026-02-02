DROP TABLE IF EXISTS resource_metrics; -- drop child table first
DROP TABLE IF EXISTS quantum_jobs;

CREATE TABLE quantum_jobs(
    job_id VARCHAR(50) PRIMARY KEY,
    backend_name VARCHAR(50) NOT NULL,
    shots INTEGER NOT NULL,

    -- circuit properties
    circuit_depth INTEGER,
    gate_count INTEGER, 

    -- staus of job
    status VARCHAR(50) NOT NULL, 

    -- time stamps
    submitted_at TIMESTAMP DEFAULT NOW(), 
    transpilation_start_at TIMESTAMP,
    transpilation_end_at TIMESTAMP,
    cr_created_at TIMESTAMP,
    qpu_start_at TIMESTAMP,
    qpu_end_at TIMESTAMP,
    completed_at TIMESTAMP, 

    -- Durations (milliseconds)
    transpilation_duration_ms INTEGER,
    simulation_duration_ms INTEGER,
    total_duration_ms INTEGER,

    -- Additional metadata
    error_message TEXT,

    -- Indexes
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_job_status ON quantum_jobs(status);
CREATE INDEX idx_backend ON quantum_jobs(backend_name);
CREATE INDEX idx_submitted_at ON quantum_jobs(submitted_at);
CREATE INDEX idx_completed_at ON quantum_jobs(completed_at);

CREATE TABLE resource_metrics(
    id serial PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    labels JSONB,
    job_id VARCHAR(50) REFERENCES quantum_jobs(job_id) ON DELETE CASCADE -- setting up foriegn key
);
CREATE INDEX idx_resource_timestamp ON resource_metrics(timestamp);
CREATE INDEX idx_metric_name ON resource_metrics(metric_name);

SELECT 'Quantum Jobs' AS label;
SELECT * FROM quantum_jobs;

SELECT 'Resource Metrics' AS label;
SELECT * FROM resource_metrics;