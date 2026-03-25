#![allow(clippy::missing_errors_doc)]
#![allow(clippy::unnecessary_struct_initialization)]
#![allow(clippy::unused_async)]
use axum::http::StatusCode;
use loco_rs::{controller::ErrorDetail, prelude::*};
use sea_orm::PaginatorTrait;
use serde::{Deserialize, Serialize};
use serde_json;

use crate::models::_entities::{articles, article_tags, favorites, followers, tags, users};
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

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Params {
    pub title: String,
    pub description: String,
    pub body: String,
    pub tagList: Vec<String>,
}

impl Params {
    fn apply_to_model(&self, item: &mut ActiveModel, author_id: i32) {
        item.slug = Set(self.title.to_lowercase().replace(' ', "-").replace("..", ""));
        item.title = Set(self.title.clone());
        item.description = Set(Some(self.description.clone()));
        item.body = Set(self.body.clone());
        item.author_id = Set(author_id);
    }
}
async fn load_by_id(ctx: &AppContext, id: i32) -> Result<Model> {
    let item = Entity::find_by_id(id).one(&ctx.db).await?;
    item.ok_or_else(|| Error::NotFound)
}

async fn load_by_slug(ctx: &AppContext, slug: &str) -> Result<Model> {
    let item = Entity::find()
        .filter(articles::Column::Slug.eq(slug.to_string()))
        .one(&ctx.db)
        .await?;
    item.ok_or_else(|| Error::NotFound)
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

    let mut tags_data = vec![];
    for at in article_tags::Entity::find()
        .filter(article_tags::Column::ArticleId.eq(article.id))
        .all(&ctx.db)
        .await?
    {
        if let Some(tag) = tags::Entity::find_by_id(at.tag_id).one(&ctx.db).await? {
            tags_data.push(tag.name);
        }
    }

    let favorites_count = favorites::Entity::find()
        .filter(favorites::Column::ArticleId.eq(article.id))
        .count(&ctx.db)
        .await?;

    let favorited = if let Some(user_id) = current_user_id {
        favorites::Entity::find()
            .filter(
                favorites::Column::ArticleId
                    .eq(article.id)
                    .and(favorites::Column::UserId.eq(user_id)),
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
        body: if include_body {
            Some(article.body.clone())
        } else {
            None
        },
        tagList: tags_data,
        createdAt: article.created_at.to_rfc3339(),
        updatedAt: article.updated_at.to_rfc3339(),
        favorited,
        favoritesCount: favorites_count as i64,
        author,
    })
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
            .all(&ctx.db)
            .await?
    };

    let mut results = vec![];
    for article in articles_list {
        let data = build_article_data(&ctx, &article, Some(current_user.id), false).await?;
        results.push(data);
    }

    let count = results.len();
    format::json(MultipleArticlesResponse {
        articles: results,
        articlesCount: count,
    })
}

#[debug_handler]
pub async fn list_global(
    State(ctx): State<AppContext>,
    Query(tag): Query<Option<String>>,
    Query(author): Query<Option<String>>,
    Query(favorited): Query<Option<String>>,
) -> Result<Response> {
    let mut query = Entity::find();

    if let Some(author_name) = author {
        if let Some(author_user) = users::Entity::find()
            .filter(users::Column::Name.eq(author_name.clone()))
            .one(&ctx.db)
            .await?
        {
            query = query.filter(articles::Column::AuthorId.eq(author_user.id));
        } else {
            return format::json(MultipleArticlesResponse {
                articles: vec![],
                articlesCount: 0,
            });
        }
    }

    if let Some(tag_name) = tag {
        let tag = tags::Entity::find()
            .filter(tags::Column::Name.eq(tag_name.clone()))
            .one(&ctx.db)
            .await?;
        let tag = match tag {
            Some(tag) => tag,
            None => {
                return format::json(MultipleArticlesResponse {
                    articles: vec![],
                    articlesCount: 0,
                })
            }
        };

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

        query = query.filter(articles::Column::Id.is_in(article_ids));
    }

    if let Some(favorited_by) = favorited {
        if let Some(fav_user) = users::Entity::find()
            .filter(users::Column::Name.eq(favorited_by.clone()))
            .one(&ctx.db)
            .await?
        {
            let article_ids: Vec<i32> = favorites::Entity::find()
                .filter(favorites::Column::UserId.eq(fav_user.id))
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

            query = query.filter(articles::Column::Id.is_in(article_ids));
        } else {
            return format::json(MultipleArticlesResponse {
                articles: vec![],
                articlesCount: 0,
            });
        }
    }

    let articles_list = query.all(&ctx.db).await?;
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
    let articles_list = Entity::find().all(&ctx.db).await?;
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
pub async fn add(
    State(ctx): State<AppContext>,
    auth: auth::JWT,
    Json(params): Json<Params>,
) -> Result<Response> {
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
    if params.description.trim().is_empty() {
        return Err(Error::CustomError(
            StatusCode::UNPROCESSABLE_ENTITY,
            ErrorDetail {
                error: None,
                description: None,
                errors: Some(serde_json::json!({"description": ["can't be blank"]})),
            },
        ));
    }
    if params.body.trim().is_empty() {
        return Err(Error::CustomError(
            StatusCode::UNPROCESSABLE_ENTITY,
            ErrorDetail {
                error: None,
                description: None,
                errors: Some(serde_json::json!({"body": ["can't be blank"]})),
            },
        ));
    }

    let current_user = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;

    let mut item = ActiveModel {
        ..Default::default()
    };
    params.apply_to_model(&mut item, current_user.id);

    let item = item.insert(&ctx.db).await?;

    let data = build_article_data(&ctx, &item, Some(current_user.id), true).await?;

    format::render().status(StatusCode::CREATED).json(SingleArticleResponse { article: data })
}

#[debug_handler]
pub async fn update(
    Path(slug): Path<String>,
    State(ctx): State<AppContext>,
    auth: auth::JWT,
    Json(params): Json<Params>,
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

    let mut active = item.into_active_model();
    params.apply_to_model(&mut active, current_user.id);
    let item = active.update(&ctx.db).await?;

    let data = build_article_data(&ctx, &item, Some(current_user.id), true).await?;

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
pub async fn get_one_by_slug(Path(slug): Path<String>, State(ctx): State<AppContext>) -> Result<Response> {
    let article = load_by_slug(&ctx, &slug).await?;
    let data = build_article_data(&ctx, &article, None, true).await?;
    format::json(SingleArticleResponse { article: data })
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
            created_at: Set(Some(chrono::Utc::now().into())),
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

pub fn routes() -> Routes {
    Routes::new()
        .prefix("api/articles/")
        .add("/feed", get(list_feed))
        .add("/", get(list_global))
        .add("/", post(add))
        .add("{slug}", get(get_one_by_slug))
        .add("{slug}", delete(remove))
        .add("{slug}", put(update))
        .add("{slug}", patch(update))
        .add("{slug}/favorite", post(favorite_article))
        .add("{slug}/favorite", delete(unfavorite_article))
}
