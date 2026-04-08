use serde::{Deserialize, Serialize};

/// Wraps any inner type as `{ "user": T }` for request deserialization.
/// Matches the RealWorld API spec: POST /api/users, POST /api/users/login, etc.
#[derive(Debug, Deserialize)]
pub struct UserEnvelope<T> {
    pub user: T,
}

/// Register request DTO — mirrors `RegisterParams` but nested under `user` key.
#[derive(Debug, Deserialize, Serialize)]
pub struct RegisterRequest {
    pub username: String,
    pub email: String,
    pub password: String,
}

/// Login request DTO — nested under `user` key.
#[derive(Debug, Deserialize, Serialize)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
}

/// Forgot-password request DTO.
#[derive(Debug, Deserialize, Serialize)]
pub struct ForgotRequest {
    pub email: String,
}

/// Reset-password request DTO.
#[derive(Debug, Deserialize, Serialize)]
pub struct ResetRequest {
    pub token: String,
    pub password: String,
}

/// Magic-link request DTO.
#[derive(Debug, Deserialize, Serialize)]
pub struct MagicLinkRequest {
    pub email: String,
}

/// Resend-verification request DTO.
#[derive(Debug, Deserialize, Serialize)]
pub struct ResendVerificationRequest {
    pub email: String,
}