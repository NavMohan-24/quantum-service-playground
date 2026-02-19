import sys
from utils.metricsDB import MetricsDB



print("Start of test..\n")

print("Checking connection ..\n")
try:
    metricsdb = MetricsDB()
    print("✅ connected to DB.")
except Exception as e:
   raise RuntimeError(f"❌ Failed to initialize DB: {e}")

print('Creating job entry..\n')

try:
    metricsdb.create_job(job_id="qjob-001", backend_name="ibm_fez", shots="2029")
    metricsdb.create_job(job_id="qjob-002", backend_name="ibm_kyoto", shots="5920")
    metricsdb.create_job(job_id="qjob-003", backend_name="ibm_marrakkesh", shots="1024")

    print("✅ Added job entries..")
except Exception as e:
    raise RuntimeError(f"❌ Failed to add job entries: {e}")

try:
    metricsdb.update_transpiler_start(job_id='qjob-001')
    metricsdb.update_transpiler_start(job_id='qjob-002')
    metricsdb.update_transpiler_start(job_id='qjob-003')

    print("✅ Updated start time..")
except Exception as e:
    raise RuntimeError(f"❌ Failed to update transpiler start: {e}")

try:
    metricsdb.update_transpile_complete(job_id="qjob-001", duration_ms= 100, circuit_depth= [500,200], one_q_gate_count= [1234,244], two_q_gate_count= [298,213])
    metricsdb.update_transpile_complete(job_id="qjob-002", duration_ms= 252, circuit_depth= [256,2445], one_q_gate_count= [121,200], two_q_gate_count= [154,100])
    metricsdb.update_transpile_complete(job_id="qjob-003", duration_ms= 50, circuit_depth= [100], one_q_gate_count= [145], two_q_gate_count= [20])

    print("✅ Update transpile complete time..")

except Exception as e:
    raise RuntimeError(f"❌ Failed to mark completion of transpiler: {e}")



try:
    metricsdb.update_simulation_start(job_id='qjob-001')
    print("✅ updated start of simulation ..")

except Exception as e:
    raise RuntimeError(f"❌ Failed to mark start of simulation: {e}")

try:
    metricsdb.update_simulation_complete(job_id="qjob-001", pod_name='batpod')

except Exception as e:
    raise RuntimeError(f"❌ Failed to mark completion of simulation: {e}")

try:
    metricsdb.update_job_complete(job_id="qjob-001")
    print("✅ updated completion of the job..")

except Exception as e:
    raise RuntimeError(f"❌ Failed to mark completion of job: {e}")

try:
    metricsdb.update_job_failed(job_id="qjob-002", error_message='tsunami')
    print("✅ updated completion of the job..")

except Exception as e:
    raise RuntimeError(f"❌ Failed to mark failure of job: {e}")

try:
    metricsdb.record_resource_metrics(job_id="qjob-001", metric_name='cpu-usage', metric_value=25.0)
    print("✅ updated resource metrics..")
except Exception as e:
    raise RuntimeError(f"❌ Failed to record resource metrics: {e}")

try:
    dict = metricsdb.get_job_metrics(job_id='qjob-001')
    print(f"✅ fetch metrics of a job : {dict}")

except Exception as e:
    raise RuntimeError(f"❌ Failed to fetch metrics: {e}")
try:
    metricsdb.close()
    print("✅ closed connection to db..")
except Exception as e:
    raise RuntimeError(f"❌ Failed to close the connection: {e}")

