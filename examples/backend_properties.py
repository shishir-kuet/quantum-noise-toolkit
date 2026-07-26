from pprint import pprint
from qiskit_ibm_runtime.ibm_backend import IBMBackend
from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService()

backend = service.backend("ibm_fez")
assert isinstance(backend, IBMBackend)
print("=" * 60)
print(type(backend.properties()))
print("=" * 60)

props = backend.properties()

print(props)

print()

print("=" * 60)
print("DIR")
print("=" * 60)

pprint(dir(props))
