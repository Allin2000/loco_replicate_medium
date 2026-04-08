// src/dto/comment.rs

use serde::{Deserialize, Serialize};

// ==================== Request DTO ====================

#[derive(Debug, Clone, Deserialize)]
pub struct CreateCommentRequest {
    pub comment: CreateCommentParams,
}

#[derive(Debug, Clone, Deserialize)]
pub struct CreateCommentParams {
    pub body: String,
}

// ==================== Response DTO ====================

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CommentAuthor {
    pub username: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CommentData {
    pub id: i32,
    pub created_at: String,
    pub updated_at: String,
    pub body: String,
    pub author: CommentAuthor,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SingleCommentResponse {
    pub comment: CommentData,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CommentsResponse {
    pub comments: Vec<CommentData>,
}