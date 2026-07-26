from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService()

backends = service.backends()

print(f"Total backends: {len(backends)}")

for backend in backends:
    print(backend.name)