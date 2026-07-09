def verification_resend_key(user_id: int) -> str:
    return f"user:{user_id}:verification:resend-lock"