// src/controllers/article.rs
#![allow(clippy::missing_errors_doc)]
#![allow(clippy::unnecessary_struct_initialization)]
#![allow(clippy::unused_async)]

use axum::http::StatusCode;
use loco_rs::{controller::ErrorDetail, prelude::*};
use sea_orm::{ActiveModelTrait, ColumnTrait, EntityTrait, PaginatorTrait, QueryFilter, QueryOrder, Set};
use serde::Serialize;
use serde_json;
use chrono::Utc;

use crate::dto::article::{
    ArticleListQuery, CreateArticleEnvelope, TagListIntent,
    UpdateArticleEnvelope,
};
use crate::models::_entities::{
    articles, article_tags, favorites, followers, tags, users,
};
use crate::models::_entities::articles::{ActiveModel, Entity, Model};

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

// ====================== 辅助函数 ======================

async fn load_by_slug(ctx: &AppContext, slug: &str) -> Result<Model> {
    Entity::find()
        .filter(articles::Column::Slug.eq(slug))
        .one(&ctx.db)
        .await?
        .ok_or_else(|| Error::NotFound)
}

async fn load_author(ctx: &AppContext, author_id: i32) -> Result<users::Model> {
    users::Entity::find_by_id(author_id)
        .one(&ctx.db)
        .await?
        .ok_or_else(|| Error::NotFound)
}

async fn load_tags(ctx: &AppContext, article_id: i32) -> Result<Vec<String>> {
    let links = article_tags::Entity::find()
        .filter(article_tags::Column::ArticleId.eq(article_id))
        .all(&ctx.db)
        .await?;

    let mut tags_data = vec![];
    for link in links {
        if let Some(tag) = tags::Entity::find_by_id(link.tag_id).one(&ctx.db).await? {
            tags_data.push(tag.name);
        }
    }
    Ok(tags_data)
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
            // 删除旧关联
            article_tags::Entity::delete_many()
                .filter(article_tags::Column::ArticleId.eq(article_id))
                .exec(&ctx.db)
                .await?;

            // 插入新标签（支持空数组）
            for tag_name in new_tags {
                let tag = if let Some(t) = tags::Entity::find()
                    .filter(tags::Column::Name.eq(&tag_name))
                    .one(&ctx.db)
                    .await?
                {
                    t
                } else {
                    let now = Utc::now();
                    let new_tag = tags::ActiveModel {
                        name: Set(tag_name.clone()),
                        created_at: Set(now.into()),
                        ..Default::default()
                    };
                    new_tag.insert(&ctx.db).await?
                };

                let link = article_tags::ActiveModel {
                    article_id: Set(article_id),
                    tag_id: Set(tag.id),
                    ..Default::default()
                };
                link.insert(&ctx.db).await?;
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
    let author_user = load_author(ctx, article.author_id).await?;
    let tagList = load_tags(ctx, article.id).await?;

    let favorites_count: u64 = favorites::Entity::find()
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

    let author = ArticleAuthor {
        username: author_user.name.clone(),
        bio: author_user.bio.clone(),
        image: author_user.image.clone(),
        following: false,
    };

    Ok(ArticleData {
        slug: article.slug.clone(),
        title: article.title.clone(),
        description: article.description.clone(),
        body: if include_body { Some(article.body.clone()) } else { None },
        tagList,
        createdAt: article.created_at.to_rfc3339(),
        updatedAt: article.updated_at.to_rfc3339(),
        favorited,
        favoritesCount: favorites_count as i64,
        author,
    })
}

// ====================== 控制器 ======================

#[debug_handler]
pub async fn list_global(
    State(ctx): State<AppContext>,
    Query(query): Query<ArticleListQuery>,
) -> Result<Response> {
    let mut q = Entity::find().order_by_desc(articles::Column::CreatedAt);

    if let Some(author_name) = query.author {
        if let Some(user) = users::Entity::find()
            .filter(users::Column::Name.eq(author_name))
            .one(&ctx.db)
            .await?
        {
            q = q.filter(articles::Column::AuthorId.eq(user.id));
        } else {
            return format::json(MultipleArticlesResponse {
                articles: vec![],
                articlesCount: 0,
            });
        }
    }

    if let Some(tag_name) = query.tag {
        if let Some(tag) = tags::Entity::find()
            .filter(tags::Column::Name.eq(tag_name))
            .one(&ctx.db)
            .await?
        {
            let article_ids: Vec<i32> = article_tags::Entity::find()
                .filter(article_tags::Column::TagId.eq(tag.id))
                .all(&ctx.db)
                .await?
                .into_iter()
                .map(|at| at.article_id)
                .collect();

            if article_ids.is_empty() {
                return format::json(MultipleArticlesResponse {
                    articles: vec![],
                    articlesCount: 0,
                });
            }
            q = q.filter(articles::Column::Id.is_in(article_ids));
        } else {
            return format::json(MultipleArticlesResponse {
                articles: vec![],
                articlesCount: 0,
            });
        }
    }

    if let Some(fav_by) = query.favorited {
        if let Some(user) = users::Entity::find()
            .filter(users::Column::Name.eq(fav_by))
            .one(&ctx.db)
            .await?
        {
            let article_ids: Vec<i32> = favorites::Entity::find()
                .filter(favorites::Column::UserId.eq(user.id))
                .all(&ctx.db)
                .await?
                .into_iter()
                .map(|f| f.article_id)
                .collect();

            if article_ids.is_empty() {
                return format::json(MultipleArticlesResponse {
                    articles: vec![],
                    articlesCount: 0,
                });
            }
            q = q.filter(articles::Column::Id.is_in(article_ids));
        } else {
            return format::json(MultipleArticlesResponse {
                articles: vec![],
                articlesCount: 0,
            });
        }
    }

    let articles_list = q.all(&ctx.db).await?;
    let mut results = vec![];

    for article in articles_list {
        results.push(build_article_data(&ctx, &article, None, false).await?);
    }

    let count = results.len();
    format::json(MultipleArticlesResponse {
        articles: results,
        articlesCount: count,
    })
}

#[debug_handler]
pub async fn list(State(ctx): State<AppContext>) -> Result<Response> {
    list_global(State(ctx), Query(ArticleListQuery::default())).await
}

#[debug_handler]
pub async fn list_feed(State(ctx): State<AppContext>, auth: auth::JWT) -> Result<Response> {
    let current_user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;
    let following_ids: Vec<i32> = followers::Entity::find()
        .filter(followers::Column::FollowerId.eq(current_user.id))
        .all(&ctx.db)
        .await?
        .into_iter()
        .map(|f| f.following_id)
        .collect();

    let articles_list = if following_ids.is_empty() {
        vec![]
    } else {
        Entity::find()
            .filter(articles::Column::AuthorId.is_in(following_ids))
            .order_by_desc(articles::Column::CreatedAt)
            .all(&ctx.db)
            .await?
    };

    let mut results = vec![];
    for article in articles_list {
        results.push(build_article_data(&ctx, &article, Some(current_user.id), false).await?);
    }

    let count = results.len();
    format::json(MultipleArticlesResponse {
        articles: results,
        articlesCount: count,
    })
}

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
    item.slug = Set(params.title.to_lowercase().replace(' ', "-").replace(['.', ','], ""));
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
    let mut active: ActiveModel = item.into_active_model();

    req.apply_scalars(&mut active);
    let updated = active.update(&ctx.db).await?;

    handle_tags_update(&ctx, updated.id, req.tag_list.intent()).await?;

    let data = build_article_data(&ctx, &updated, Some(current_user.id), true).await?;
    format::json(SingleArticleResponse { article: data })
}

#[debug_handler]
pub async fn get_one_by_slug(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
) -> Result<Response> {
    let article = load_by_slug(&ctx, &slug).await?;
    let data = build_article_data(&ctx, &article, None, true).await?;
    format::json(SingleArticleResponse { article: data })
}


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
        let fav = favorites::ActiveModel {
            user_id: Set(user.id),
            article_id: Set(article.id),
            ..Default::default()
        };
        fav.insert(&ctx.db).await?;
    }

    let reloaded = load_by_slug(&ctx, &slug).await?;
    let data = build_article_data(&ctx, &reloaded, Some(user.id), true).await?;
    format::json(SingleArticleResponse { article: data })
}

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

// ====================== 路由 ======================
pub fn routes() -> Routes {
    Routes::new()
        .prefix("api/articles")
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