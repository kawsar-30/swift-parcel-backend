from fastapi import HTTPException

STATUS_TRANSITIONS = {
    "PENDING": ["PICKUP_ASSIGNED", "CANCELLED"],
    "PICKUP_ASSIGNED": ["PICKED_UP", "PENDING"],
    "PICKED_UP": ["AT_HUB"],
    "AT_HUB": ["IN_TRANSIT", "OUT_FOR_DELIVERY"],
    "IN_TRANSIT": ["AT_HUB", "OUT_FOR_DELIVERY"],
    "OUT_FOR_DELIVERY": ["DELIVERED", "FAILED_ATTEMPT"],
    "FAILED_ATTEMPT": ["OUT_FOR_DELIVERY", "RETURNED"],
    "DELIVERED": [],
    "RETURNED": [],
    "CANCELLED": []
}

def validate_status_transition(current_status: str, new_status: str):
    # Jodi current_status "RECEIVED_AT_" diye shuru hoy, 
    # tahole OUT_FOR_DELIVERY allow koro
    if current_status.startswith("RECEIVED_AT_"):
        if new_status not in ["OUT_FOR_DELIVERY"]:
            raise HTTPException(
                status_code=409,
                detail="Only OUT_FOR_DELIVERY is allowed from RECEIVED_AT_ status."
            )
        return

    # Jodi new_status "RECEIVED_AT_" diye shuru hoy, tahole allow koro
    if new_status.startswith("RECEIVED_AT_"):
        if current_status != "IN_TRANSIT":
            raise HTTPException(
                status_code=409,
                detail="Only IN_TRANSIT parcels can be received at a hub."
            )
        return

    # Normal transition check
    allowed = STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=409, 
            detail=f"Invalid transition from {current_status} to {new_status}. Allowed: {allowed}"
        )