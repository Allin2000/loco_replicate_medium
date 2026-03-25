#![allow(clippy::missing_errors_doc)]
#![allow(clippy::unnecessary_struct_initialization)]
#![allow(clippy::unused_async)]
use axum::http::StatusCode;
use loco_rs::prelude::*;
use serde::{Deserialize, Serialize};

use crate::models::_entities::{articles, comments, users};
use crate::models::_entities::comments::{Entity, Model};

#[derive(Debug, Serialize)]
pub struct CommentAuthor {
    pub username: String,
}

#[derive(Debug, Serialize)]
pub struct CommentData {
    pub id: i32,
    pub createdAt: String,
    pub updatedAt: String,
    pub body: String,
    pub author: CommentAuthor,
}

#[derive(Debug, Serialize)]
pub struct CommentsResponse {
    pub comments: Vec<CommentData>,
}

#[derive(Debug, Serialize)]
pub struct SingleCommentResponse {
    pub comment: CommentData,
}

async fn comment_to_data(ctx: &AppContext, comment: &Model) -> Result<CommentData> {
    let user = users::Entity::find_by_id(comment.user_id)
        .one(&ctx.db)
        .await?
        .ok_or_else(|| Error::NotFound)?;

    Ok(CommentData {
        id: comment.id,
        createdAt: comment.created_at.to_rfc3339(),
        updatedAt: comment.updated_at.to_rfc3339(),
        body: comment.body.clone(),
        author: CommentAuthor {
            username: user.name.clone(),
        },
    })
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CreateCommentParams {
    pub body: String,
}

async fn load_article_by_slug(ctx: &AppContext, slug: &str) -> Result<articles::Model> {
    let article = articles::Entity::find()
        .filter(articles::Column::Slug.eq(slug.to_string()))
        .one(&ctx.db)
        .await?;
    article.ok_or_else(|| Error::NotFound)
}

async fn load_comment_by_id(ctx: &AppContext, comment_id: i32) -> Result<Model> {
    let item = Entity::find_by_id(comment_id).one(&ctx.db).await?;
    item.ok_or_else(|| Error::NotFound)
}

#[debug_handler]
pub async fn list(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
) -> Result<Response> {
    let article = load_article_by_slug(&ctx, &slug).await?;
    let comments_list = Entity::find()
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
    Json(params): Json<CreateCommentParams>,
) -> Result<Response> {
    let article = load_article_by_slug(&ctx, &slug).await?;
    let current_user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;

    let comment = comments::ActiveModel {
        body: Set(params.body.clone()),
        article_id: Set(article.id),
        user_id: Set(current_user.id),
        ..Default::default()
    };
    let item = comment.insert(&ctx.db).await?;

    let response_data = comment_to_data(&ctx, &item).await?;
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
        return bad_request("Comment does not belong to article");
    }

    if comment.user_id != users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?.id {
        return unauthorized("unauthorized!");
    }

    comment.delete(&ctx.db).await?;
    format::render().status(StatusCode::NO_CONTENT).empty()
}

pub fn routes() -> Routes {
    Routes::new()
        .prefix("/api/articles")
        .add("/{slug}/comments", get(list))
        .add("/{slug}/comments", post(create))
        .add("/{slug}/comments/{id}", delete(remove))
}
