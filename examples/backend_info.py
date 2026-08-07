from pprint import pprint

from qiskit_ibm_runtime import QiskitRuntimeService

from qntoolkit.backend import get_backend_info

service = QiskitRuntimeService()

info = get_backend_info(service, "ibm_fez")

pprint(info)