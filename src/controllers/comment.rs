// src/controllers/comment.rs
#![allow(clippy::missing_errors_doc)]
#![allow(clippy::unnecessary_struct_initialization)]
#![allow(clippy::unused_async)]

use axum::http::StatusCode;
use loco_rs::prelude::*;

use crate::dto::comment::{
    CommentAuthor, CommentData, CommentsResponse, CreateCommentRequest, SingleCommentResponse,
};
use crate::models::_entities::{articles, comments, users};

async fn comment_to_data(ctx: &AppContext, comment: &comments::Model) -> Result<CommentData> {
    let user = users::Entity::find_by_id(comment.user_id)
        .one(&ctx.db)
        .await?
        .ok_or_else(|| Error::NotFound)?;

    Ok(CommentData {
        id: comment.id,
        created_at: comment.created_at.to_rfc3339(),
        updated_at: comment.updated_at.to_rfc3339(),
        body: comment.body.clone(),
        author: CommentAuthor {
            username: user.name.clone(),        // 如果模型字段是 username，请改为 user.username.clone()
        },
    })
}

async fn load_article_by_slug(ctx: &AppContext, slug: &str) -> Result<articles::Model> {
    let article = articles::Entity::find()
        .filter(articles::Column::Slug.eq(slug.to_string()))
        .one(&ctx.db)
        .await?
        .ok_or_else(|| Error::NotFound)?;

    Ok(article)
}

async fn load_comment_by_id(ctx: &AppContext, comment_id: i32) -> Result<comments::Model> {
    let item = comments::Entity::find_by_id(comment_id)
        .one(&ctx.db)
        .await?
        .ok_or_else(|| Error::NotFound)?;

    Ok(item)
}

#[debug_handler]
pub async fn list(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
) -> Result<Response> {
    let article = load_article_by_slug(&ctx, &slug).await?;

    let comments_list = comments::Entity::find()
        .filter(comments::Column::ArticleId.eq(article.id))
        .all(&ctx.db)
        .await?;

    let mut data = vec![];
    for comment in comments_list {
        data.push(comment_to_data(&ctx, &comment).await?);
    }

    format::json(CommentsResponse { comments: data })
}

#[debug_handler]
pub async fn create(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
    auth: auth::JWT,
    Json(request): Json<CreateCommentRequest>,
) -> Result<Response> {
    let article = load_article_by_slug(&ctx, &slug).await?;
    let current_user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;

    let params = request.comment;

    let comment = comments::ActiveModel {
        body: Set(params.body),
        article_id: Set(article.id),
        user_id: Set(current_user.id),
        ..Default::default()
    };

    let item = comment.insert(&ctx.db).await?;
    let response_data = comment_to_data(&ctx, &item).await?;

    // 正确写法：直接返回 Result，不需要包 Ok()
    format::render()
        .status(StatusCode::CREATED)
        .json(SingleCommentResponse { comment: response_data })
}

#[debug_handler]
pub async fn remove(
    Path((slug, id)): Path<(String, i32)>,
    State(ctx): State<AppContext>,
    auth: auth::JWT,
) -> Result<Response> {
    let article = load_article_by_slug(&ctx, &slug).await?;
    let comment = load_comment_by_id(&ctx, id).await?;

    if comment.article_id != article.id {
        return Err(Error::BadRequest("Comment does not belong to article".into()));
    }

    let current_user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;
    if comment.user_id != current_user.id {
        return Err(Error::Unauthorized("unauthorized!".into()));
    }

    comment.delete(&ctx.db).await?;

    // 正确写法：直接返回 Result
    format::render().status(StatusCode::NO_CONTENT).empty()
}

pub fn routes() -> Routes {
    Routes::new()
        .prefix("/api/articles")
        .add("/{slug}/comments", get(list))
        .add("/{slug}/comments", post(create))
        .add("/{slug}/comments/{id}", delete(remove))
}