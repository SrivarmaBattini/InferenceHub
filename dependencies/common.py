from fastapi import Header, HTTPException

def verify_api_version(x_api_version: str | None = Header(default=None)):
    """
    Reject requests that specify an unsupported API version header.
    If no header is sent, allow through (backwards compatible).
    """
    supported = {"1", "2"}
    if x_api_version is not None and x_api_version not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported API version: {x_api_version}. Supported: {supported}",
        )