from pprint import pprint

import matplotlib.pyplot as plt
import rustworkx as rx
from qiskit_ibm_runtime import QiskitRuntimeService

# -------------------------------------------------
# Connect
# -------------------------------------------------

service = QiskitRuntimeService()

backend = service.backend("ibm_fez")

target = backend.target

assert target is not None

print(target.build_coupling_map())
# -------------------------------------------------
# Basic backend information
# -------------------------------------------------

print("=" * 60)
print("Backend")
print("=" * 60)

print("Name:", backend.name)
print("Version:", backend.backend_version)
print("Qubits:", backend.num_qubits)

print()

# -------------------------------------------------
# Target information
# -------------------------------------------------

print("=" * 60)
print("Target")
print("=" * 60)

print(type(target))
print()

print("Operations")
print(target.operation_names)

print()

print("Coupling Map")
print(target.build_coupling_map().get_edges())

print()

print("Instruction count:", len(target.instructions))

print()

print("Target API")
pprint(dir(target))

# -------------------------------------------------
# Draw coupling graph
# -------------------------------------------------

coupling = target.build_coupling_map()

graph = rx.PyGraph()

graph.add_nodes_from(range(backend.num_qubits))

graph.add_edges_from_no_data(coupling.get_edges())

plt.figure(figsize=(15, 15))

rx.visualization.mpl_draw(
    graph,
    with_labels=True,
    node_size=70,
    font_size=6,
)

plt.title(backend.name + " Coupling Map")

plt.show()