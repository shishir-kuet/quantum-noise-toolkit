import warnings

from qiskit.providers import BackendV2
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService, fake_provider

from qntoolkit.utils.exceptions import (
    BackendNotFoundError,
    ServiceNotInitializedError,
)


def get_simulator() -> AerSimulator:
    """Return the local Aer simulator."""
    return AerSimulator()


def get_backend(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return an IBM Quantum backend."""

    if service is None:
        raise ServiceNotInitializedError("Runtime service is not initialized.")

    if not backend_exists(service, backend_name):
        raise BackendNotFoundError(f"Backend '{backend_name}' not found.")

    return service.backend(backend_name)


def list_backends(service: QiskitRuntimeService) -> list[str]:
    """Return available backend names."""

    if service is None:
        raise ServiceNotInitializedError("Runtime service is not initialized.")

    return sorted(backend.name for backend in service.backends() if backend.name is not None)


def backend_exists(
    service: QiskitRuntimeService,
    backend_name: str,
) -> bool:
    """Check whether a backend exists."""

    return backend_name in list_backends(service)


def list_fake_backends() -> list[str]:
    """Return the names of the offline fake backends shipped with Qiskit."""

    # Some fake backends warn on construction that their data is synthetic.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        backends = fake_provider.FakeProviderForBackendV2().backends()

    return sorted(backend.name for backend in backends)


def get_fake_backend(backend_name: str) -> BackendV2:
    """Return an offline fake backend, e.g. ``"fake_fez"`` or ``"fake_manila"``.

    Fake backends carry a snapshot of real device calibration data, which makes
    them ideal for testing and for working without IBM Quantum credentials.
    """

    # "fake_manila" -> FakeManilaV2 / FakeManila. Looking the class up
    # directly avoids instantiating every fake backend in the provider.
    stem = "".join(part.capitalize() for part in backend_name.removeprefix("fake_").split("_"))

    for class_name in (f"Fake{stem}V2", f"Fake{stem}"):
        backend_class = getattr(fake_provider, class_name, None)

        if backend_class is not None:
            backend = backend_class()

            if isinstance(backend, BackendV2) and backend.name == backend_name:
                return backend

    raise BackendNotFoundError(
        f"Fake backend '{backend_name}' not found. "
        "Use list_fake_backends() to see the available names."
    )


def load_backend(
    backend_name: str,
    service: QiskitRuntimeService | None = None,
) -> BackendV2:
    """Load a backend by name.

    - ``"aer_simulator"`` returns the local Aer simulator.
    - Names starting with ``"fake_"`` return an offline fake backend.
    - Any other name is looked up on IBM Quantum. If ``service`` is not
      given, a :class:`QiskitRuntimeService` is created from the saved
      account credentials.
    """

    if backend_name == "aer_simulator":
        return get_simulator()

    if backend_name.startswith("fake_"):
        return get_fake_backend(backend_name)

    if service is None:
        try:
            service = QiskitRuntimeService()
        except Exception as error:
            raise ServiceNotInitializedError(
                "Could not initialize QiskitRuntimeService. Save your IBM "
                "Quantum credentials with QiskitRuntimeService.save_account()."
            ) from error

    return get_backend(service, backend_name)
