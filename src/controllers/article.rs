// src/controllers/article.rs
#![allow(clippy::missing_errors_doc)]
#![allow(clippy::unnecessary_struct_initialization)]
#![allow(clippy::unused_async)]

use axum::{http::StatusCode, http::HeaderMap};
use loco_rs::{controller::ErrorDetail, prelude::*};
use sea_orm::{
    ActiveModelTrait, ColumnTrait, EntityTrait, PaginatorTrait,
    QueryFilter, QueryOrder, QuerySelect, Set,
};
use serde::Serialize;
use serde_json;
use chrono::Utc;

use crate::dto::article::{
    ArticleListQuery, CreateArticleEnvelope, TagListIntent, UpdateArticleEnvelope,
};
use crate::models::_entities::{
    article_tags, articles, favorites, followers, tags, users,
};
use crate::models::_entities::articles::{ActiveModel, Entity, Model};

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct ArticleAuthor {
    pub username: String,
    pub bio: Option<String>,
    pub image: Option<String>,
    pub following: bool,
}

#[derive(Debug, Serialize)]
pub struct ArticleData {
    pub slug: String,
    pub title: String,
    pub description: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub body: Option<String>,
    pub tagList: Vec<String>,
    pub createdAt: String,
    pub updatedAt: String,
    pub favorited: bool,
    pub favoritesCount: i64,
    pub author: ArticleAuthor,
}

#[derive(Debug, Serialize)]
pub struct SingleArticleResponse {
    pub article: ArticleData,
}

#[derive(Debug, Serialize)]
pub struct MultipleArticlesResponse {
    pub articles: Vec<ArticleData>,
    pub articlesCount: usize,
}

// ---------------------------------------------------------------------------
// Optional auth: parse Bearer token from headers without requiring login
// ---------------------------------------------------------------------------

/// Try to resolve the current user from an optional `Authorization: Bearer <token>` header.
/// Returns `None` if header is absent, malformed, or token is invalid.
async fn optional_user_id(ctx: &AppContext, headers: &HeaderMap) -> Option<i32> {
    let token = headers
        .get("authorization")
        .and_then(|v| v.to_str().ok())
        .and_then(|s| s.strip_prefix("Bearer "))?;

    let jwt_secret = ctx.config.get_jwt_config().ok()?;
    let claims = loco_rs::auth::jwt::JWT::new(&jwt_secret.secret)
        .validate(token)
        .ok()?;

    users::Model::find_by_pid(&ctx.db, &claims.claims.pid)
        .await
        .ok()
        .map(|u| u.id)
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async fn load_by_slug(ctx: &AppContext, slug: &str) -> Result<Model> {
    Entity::find()
        .filter(articles::Column::Slug.eq(slug))
        .one(&ctx.db)
        .await?
        .ok_or_else(|| Error::NotFound)
}

async fn load_tags(ctx: &AppContext, article_id: i32) -> Result<Vec<String>> {
    let links = article_tags::Entity::find()
        .filter(article_tags::Column::ArticleId.eq(article_id))
        .all(&ctx.db)
        .await?;

    let mut names = vec![];
    for link in links {
        if let Some(tag) = tags::Entity::find_by_id(link.tag_id).one(&ctx.db).await? {
            names.push(tag.name);
        }
    }
    Ok(names)
}

async fn handle_tags_update(
    ctx: &AppContext,
    article_id: i32,
    intent: TagListIntent,
) -> Result<()> {
    match intent {
        TagListIntent::Preserve => Ok(()),

        TagListIntent::Null => Err(Error::CustomError(
            StatusCode::UNPROCESSABLE_ENTITY,
            ErrorDetail {
                error: None,
                description: None,
                errors: Some(serde_json::json!({"tagList": ["can't be null"]})),
            },
        )),

        TagListIntent::Replace(new_tags) => {
            article_tags::Entity::delete_many()
                .filter(article_tags::Column::ArticleId.eq(article_id))
                .exec(&ctx.db)
                .await?;

            for tag_name in new_tags {
                let tag = if let Some(t) = tags::Entity::find()
                    .filter(tags::Column::Name.eq(&tag_name))
                    .one(&ctx.db)
                    .await?
                {
                    t
                } else {
                    let new_tag = tags::ActiveModel {
                        name: Set(tag_name.clone()),
                        created_at: Set(Utc::now().into()),
                        ..Default::default()
                    };
                    new_tag.insert(&ctx.db).await?
                };

                article_tags::ActiveModel {
                    article_id: Set(article_id),
                    tag_id: Set(tag.id),
                    ..Default::default()
                }
                .insert(&ctx.db)
                .await?;
            }
            Ok(())
        }
    }
}

async fn build_article_data(
    ctx: &AppContext,
    article: &Model,
    current_user_id: Option<i32>,
    include_body: bool,
) -> Result<ArticleData> {
    let author_user = users::Entity::find_by_id(article.author_id)
        .one(&ctx.db)
        .await?
        .ok_or_else(|| Error::NotFound)?;

    let tag_list = load_tags(ctx, article.id).await?;

    let favorites_count = favorites::Entity::find()
        .filter(favorites::Column::ArticleId.eq(article.id))
        .count(&ctx.db)
        .await?;

    let favorited = if let Some(uid) = current_user_id {
        favorites::Entity::find()
            .filter(
                favorites::Column::ArticleId
                    .eq(article.id)
                    .and(favorites::Column::UserId.eq(uid)),
            )
            .one(&ctx.db)
            .await?
            .is_some()
    } else {
        false
    };

    let following = if let Some(uid) = current_user_id {
        followers::Entity::find()
            .filter(
                followers::Column::FollowerId
                    .eq(uid)
                    .and(followers::Column::FollowingId.eq(article.author_id)),
            )
            .one(&ctx.db)
            .await?
            .is_some()
    } else {
        false
    };

    Ok(ArticleData {
        slug: article.slug.clone(),
        title: article.title.clone(),
        description: article.description.clone(),
        body: if include_body { Some(article.body.clone()) } else { None },
        tagList: tag_list,
        createdAt: article.created_at.to_rfc3339(),
        updatedAt: article.updated_at.to_rfc3339(),
        favorited,
        favoritesCount: favorites_count as i64,
        author: ArticleAuthor {
            username: author_user.name.clone(),
            bio: author_user.bio.clone(),
            image: author_user.image.clone(),
            following,
        },
    })
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

/// GET /api/articles — list with optional filters, auth optional
#[debug_handler]
pub async fn list_global(
    State(ctx): State<AppContext>,
    headers: HeaderMap,
    Query(query): Query<ArticleListQuery>,
) -> Result<Response> {
    let current_user_id = optional_user_id(&ctx, &headers).await;

    let mut q = Entity::find().order_by_desc(articles::Column::CreatedAt);

    if let Some(author_name) = query.author {
        match users::Entity::find()
            .filter(users::Column::Name.eq(author_name))
            .one(&ctx.db)
            .await?
        {
            Some(user) => q = q.filter(articles::Column::AuthorId.eq(user.id)),
            None => {
                return format::json(MultipleArticlesResponse {
                    articles: vec![],
                    articlesCount: 0,
                })
            }
        }
    }

    if let Some(tag_name) = query.tag {
        match tags::Entity::find()
            .filter(tags::Column::Name.eq(tag_name))
            .one(&ctx.db)
            .await?
        {
            Some(tag) => {
                let ids: Vec<i32> = article_tags::Entity::find()
                    .filter(article_tags::Column::TagId.eq(tag.id))
                    .all(&ctx.db)
                    .await?
                    .into_iter()
                    .map(|at| at.article_id)
                    .collect();
                if ids.is_empty() {
                    return format::json(MultipleArticlesResponse {
                        articles: vec![],
                        articlesCount: 0,
                    });
                }
                q = q.filter(articles::Column::Id.is_in(ids));
            }
            None => {
                return format::json(MultipleArticlesResponse {
                    articles: vec![],
                    articlesCount: 0,
                })
            }
        }
    }

    if let Some(fav_by) = query.favorited {
        match users::Entity::find()
            .filter(users::Column::Name.eq(fav_by))
            .one(&ctx.db)
            .await?
        {
            Some(user) => {
                let ids: Vec<i32> = favorites::Entity::find()
                    .filter(favorites::Column::UserId.eq(user.id))
                    .all(&ctx.db)
                    .await?
                    .into_iter()
                    .map(|f| f.article_id)
                    .collect();
                if ids.is_empty() {
                    return format::json(MultipleArticlesResponse {
                        articles: vec![],
                        articlesCount: 0,
                    });
                }
                q = q.filter(articles::Column::Id.is_in(ids));
            }
            None => {
                return format::json(MultipleArticlesResponse {
                    articles: vec![],
                    articlesCount: 0,
                })
            }
        }
    }

    // Count total before pagination (RealWorld spec: articlesCount = total, not page size)
    let total = q.clone().count(&ctx.db).await?;

    if let Some(offset) = query.offset {
        q = q.offset(offset);
    }
    if let Some(limit) = query.limit {
        q = q.limit(limit);
    }

    let articles_list = q.all(&ctx.db).await?;
    let mut results = vec![];
    for article in articles_list {
        results.push(build_article_data(&ctx, &article, current_user_id, false).await?);
    }

    format::json(MultipleArticlesResponse {
        articles: results,
        articlesCount: total as usize,
    })
}

/// GET /api/articles/feed — from followed authors, auth required
#[debug_handler]
pub async fn list_feed(
    State(ctx): State<AppContext>,
    headers: HeaderMap,
    auth: auth::JWT,
    Query(query): Query<ArticleListQuery>,
) -> Result<Response> {
    let current_user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;
    let _ = headers; // headers available if needed

    let following_ids: Vec<i32> = followers::Entity::find()
        .filter(followers::Column::FollowerId.eq(current_user.id))
        .all(&ctx.db)
        .await?
        .into_iter()
        .map(|f| f.following_id)
        .collect();

    if following_ids.is_empty() {
        return format::json(MultipleArticlesResponse {
            articles: vec![],
            articlesCount: 0,
        });
    }

    let mut q = Entity::find()
        .filter(articles::Column::AuthorId.is_in(following_ids))
        .order_by_desc(articles::Column::CreatedAt);

    // Count total before pagination
    let total = q.clone().count(&ctx.db).await?;

    if let Some(offset) = query.offset {
        q = q.offset(offset);
    }
    if let Some(limit) = query.limit {
        q = q.limit(limit);
    }

    let articles_list = q.all(&ctx.db).await?;
    let mut results = vec![];
    for article in articles_list {
        results.push(
            build_article_data(&ctx, &article, Some(current_user.id), false).await?,
        );
    }

    format::json(MultipleArticlesResponse {
        articles: results,
        articlesCount: total as usize,
    })
}

/// GET /api/articles/:slug — auth optional
#[debug_handler]
pub async fn get_one_by_slug(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
    headers: HeaderMap,
) -> Result<Response> {
    let current_user_id = optional_user_id(&ctx, &headers).await;
    let article = load_by_slug(&ctx, &slug).await?;
    let data = build_article_data(&ctx, &article, current_user_id, true).await?;
    format::json(SingleArticleResponse { article: data })
}

/// POST /api/articles
#[debug_handler]
pub async fn add(
    State(ctx): State<AppContext>,
    auth: auth::JWT,
    Json(envelope): Json<CreateArticleEnvelope>,
) -> Result<Response> {
    let params = envelope.article;
    let current_user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;

    if params.title.trim().is_empty() {
        return Err(Error::CustomError(
            StatusCode::UNPROCESSABLE_ENTITY,
            ErrorDetail {
                error: None,
                description: None,
                errors: Some(serde_json::json!({"title": ["can't be blank"]})),
            },
        ));
    }

    let mut item: ActiveModel = Default::default();
    item.title = Set(params.title.clone());
    item.slug = Set(params
        .title
        .to_lowercase()
        .replace(' ', "-")
        .replace(['.', ','], ""));
    item.description = Set(Some(params.description));
    item.body = Set(params.body);
    item.author_id = Set(current_user.id);

    let inserted = item.insert(&ctx.db).await?;
    handle_tags_update(&ctx, inserted.id, TagListIntent::Replace(params.tag_list)).await?;

    let data = build_article_data(&ctx, &inserted, Some(current_user.id), true).await?;
    format::render()
        .status(StatusCode::CREATED)
        .json(SingleArticleResponse { article: data })
}

/// PUT/PATCH /api/articles/:slug
#[debug_handler]
pub async fn update(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
    auth: auth::JWT,
    Json(envelope): Json<UpdateArticleEnvelope>,
) -> Result<Response> {
    let current_user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;
    let item = load_by_slug(&ctx, &slug).await?;

    if item.author_id != current_user.id {
        return Err(Error::CustomError(
            StatusCode::FORBIDDEN,
            ErrorDetail {
                error: None,
                description: None,
                errors: Some(serde_json::json!({"article": ["forbidden"]})),
            },
        ));
    }

    let req = envelope.article;

    // Validate before any DB writes
    if matches!(req.tag_list.intent(), TagListIntent::Null) {
        return Err(Error::CustomError(
            StatusCode::UNPROCESSABLE_ENTITY,
            ErrorDetail {
                error: None,
                description: None,
                errors: Some(serde_json::json!({"tagList": ["can't be null"]})),
            },
        ));
    }

    let mut active: ActiveModel = item.into_active_model();
    req.apply_scalars(&mut active);
    let updated = active.update(&ctx.db).await?;

    handle_tags_update(&ctx, updated.id, req.tag_list.intent()).await?;

    let data = build_article_data(&ctx, &updated, Some(current_user.id), true).await?;
    format::json(SingleArticleResponse { article: data })
}

/// DELETE /api/articles/:slug
#[debug_handler]
pub async fn remove(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
    auth: auth::JWT,
) -> Result<Response> {
    let current_user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;
    let item = load_by_slug(&ctx, &slug).await?;

    if item.author_id != current_user.id {
        return Err(Error::CustomError(
            StatusCode::FORBIDDEN,
            ErrorDetail {
                error: None,
                description: None,
                errors: Some(serde_json::json!({"article": ["forbidden"]})),
            },
        ));
    }

    item.delete(&ctx.db).await?;
    format::render().status(StatusCode::NO_CONTENT).empty()
}

/// POST /api/articles/:slug/favorite
#[debug_handler]
pub async fn favorite_article(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
    auth: auth::JWT,
) -> Result<Response> {
    let user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;
    let article = load_by_slug(&ctx, &slug).await?;

    let exists = favorites::Entity::find()
        .filter(
            favorites::Column::UserId
                .eq(user.id)
                .and(favorites::Column::ArticleId.eq(article.id)),
        )
        .one(&ctx.db)
        .await?
        .is_some();

    if !exists {
        favorites::ActiveModel {
            user_id: Set(user.id),
            article_id: Set(article.id),
            ..Default::default()
        }
        .insert(&ctx.db)
        .await?;
    }

    let reloaded = load_by_slug(&ctx, &slug).await?;
    let data = build_article_data(&ctx, &reloaded, Some(user.id), true).await?;
    format::json(SingleArticleResponse { article: data })
}

/// DELETE /api/articles/:slug/favorite
#[debug_handler]
pub async fn unfavorite_article(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
    auth: auth::JWT,
) -> Result<Response> {
    let user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;
    let article = load_by_slug(&ctx, &slug).await?;

    if let Some(fav) = favorites::Entity::find()
        .filter(
            favorites::Column::UserId
                .eq(user.id)
                .and(favorites::Column::ArticleId.eq(article.id)),
        )
        .one(&ctx.db)
        .await?
    {
        fav.delete(&ctx.db).await?;
    }

    let reloaded = load_by_slug(&ctx, &slug).await?;
    let data = build_article_data(&ctx, &reloaded, Some(user.id), true).await?;
    format::json(SingleArticleResponse { article: data })
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
pub fn routes() -> Routes {
    Routes::new()
        .prefix("/api/articles")
        .add("/feed", get(list_feed))
        .add("/", get(list_global))
        .add("/", post(add))
        .add("/{slug}", get(get_one_by_slug))
        .add("/{slug}", put(update))
        .add("/{slug}", patch(update))
        .add("/{slug}", delete(remove))
        .add("/{slug}/favorite", post(favorite_article))
        .add("/{slug}/favorite", delete(unfavorite_article))
}