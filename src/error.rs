// src/errors.rs
use axum::{
    http::StatusCode,
    response::{IntoResponse, Json},
};
use serde::Serialize;
use std::collections::HashMap;

/// 统一错误响应结构
#[derive(Serialize)]
pub struct ErrorResponse {
    pub errors: HashMap<String, Vec<String>>,
}

/// 通用 API 错误类型
pub struct ApiError {
    pub field: String,
    pub messages: Vec<String>,
    pub status: StatusCode,
}

impl ApiError {
    /// 创建单条错误
    pub fn new(field: impl Into<String>, message: impl Into<String>, status: StatusCode) -> Self {
        Self {
            field: field.into(),
            messages: vec![message.into()],
            status,
        }
    }

    /// 创建多条错误
    pub fn from_messages(
        field: impl Into<String>,
        messages: Vec<String>,
        status: StatusCode,
    ) -> Self {
        Self {
            field: field.into(),
            messages,
            status,
        }
    }

    // ===========================
    // 快捷方法
    // ===========================

    // 401 未认证
    pub fn unauthorized(field: impl Into<String>, message: impl Into<String>) -> Self {
        Self::new(field, message, StatusCode::UNAUTHORIZED)
    }

    pub fn token_missing() -> Self {
        Self::unauthorized("token", "is missing")
    }

    pub fn invalid_credentials() -> Self {
        Self::unauthorized("credentials", "invalid")
    }

    // 403 禁止
    pub fn forbidden(field: impl Into<String>, message: impl Into<String>) -> Self {
        Self::new(field, message, StatusCode::FORBIDDEN)
    }

    pub fn article_forbidden() -> Self {
        Self::forbidden("article", "forbidden")
    }

    pub fn comment_forbidden() -> Self {
        Self::forbidden("comment", "forbidden")
    }

    // 404 未找到
    pub fn not_found(field: impl Into<String>, message: impl Into<String>) -> Self {
        Self::new(field, message, StatusCode::NOT_FOUND)
    }

    pub fn article_not_found() -> Self {
        Self::not_found("article", "not found")
    }

    pub fn comment_not_found() -> Self {
        Self::not_found("comment", "not found")
    }

    pub fn profile_not_found() -> Self {
        Self::not_found("profile", "not found")
    }

    // 409 冲突
    pub fn conflict(field: impl Into<String>, message: impl Into<String>) -> Self {
        Self::new(field, message, StatusCode::CONFLICT)
    }

    pub fn conflict_username() -> Self {
        Self::conflict("username", "has already been taken")
    }

    pub fn conflict_email() -> Self {
        Self::conflict("email", "has already been taken")
    }

    // 422 数据校验错误
    pub fn unprocessable(field: impl Into<String>, message: impl Into<String>) -> Self {
        Self::new(field, message, StatusCode::UNPROCESSABLE_ENTITY)
    }

    pub fn blank_field(field: &str) -> Self {
        Self::unprocessable(field, "can't be blank")
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> axum::response::Response {
        let mut map = HashMap::new();
        map.insert(self.field, self.messages);
        (self.status, Json(ErrorResponse { errors: map })).into_response()
    }
}