# Build Lock Execution Boundary

A valid node profile and a valid source build lock are necessary provenance inputs but are not sufficient to start services. Meta-OS must remain fail-closed while `build_artifact_digest` is null or build status is not reproducibly verified. Execution authority remains NONE in this generation.
