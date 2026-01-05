import sys 
import os

# set default environment variable
os.environ.setdefault("SIMULATOR_SERVICE_URL", "http://aer-simulator-service:5001")
os.environ.setdefault('TRANSPILER_SERVICE_URL', 'http://transpiler-service:5002')

# function to execute the code
def execute(code_string):
    "Execute user-provided Qiskit code"

    try:
        from remote_aer_backend import RemoteAerBackend

        # sandboxing via namespace -- to limit what usercode can do
        # executing usercode in a sandbox prevents it from accessing
        # variables and any other imports in worker.py

        namespace = {
            # built in functions, types, constants and exceptions.
            "__builtins__" : __builtins__, 
            # expose the remote aer backend class
            "RemoteAerBackend" : RemoteAerBackend
        }

        # Execute the user code
        print("=" * 60)
        print("EXECUTING USER CODE")
        print("=" * 60)


        # built-in function to execute code
        # code_string is the user code in string format.
        exec(code_string, namespace)


        print("=" * 60)
        print("EXECUTION COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as e:

        import traceback

        print("=" * 60)
        print("EXECUTION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print(traceback.format_exc())
        sys.exit(1)
    

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Submit both worker code and codefile")
        sys.exit(1)

    code_file = sys.argv[1]

    if not os.path.exists(code_file):
        print(f"Error: File '{code_file}' not found")
        sys.exit(1)

    with open(code_file, 'r') as f:
        code_string = f.read()
    
    execute(code_string)
