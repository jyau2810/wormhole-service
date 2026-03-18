This directory is reserved for CA bootstrap notes.

The current implementation initializes the CA, CRL, and server certificate
inside the `ca-api` container on first boot and persists them in the named
Docker volume `ca-data`.

No checked-in certificate material is stored in this repository.

