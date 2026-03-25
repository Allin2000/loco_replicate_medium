#![allow(clippy::missing_errors_doc)]
#![allow(clippy::unnecessary_struct_initialization)]
#![allow(clippy::unused_async)]
use loco_rs::prelude::*;
use serde::{Deserialize, Serialize};

use crate::models::_entities::{followers, users};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ProfileData {
    pub username: String,
    pub bio: Option<String>,
    pub image: Option<String>,
    pub following: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ProfileResponse {
    pub profile: ProfileData,
}

async fn load_user_by_username(ctx: &AppContext, username: &str) -> Result<users::Model> {
    let user = users::Entity::find()
        .filter(users::Column::Name.eq(username))
        .one(&ctx.db)
        .await?;
    user.ok_or_else(|| Error::NotFound)
}

async fn is_following(ctx: &AppContext, follower_id: i32, following_id: i32) -> Result<bool> {
    let record = followers::Entity::find()
        .filter(
            followers::Column::FollowerId
                .eq(follower_id)
                .and(followers::Column::FollowingId.eq(following_id)),
        )
        .one(&ctx.db)
        .await?;
    Ok(record.is_some())
}

fn make_profile(user: &users::Model, following: bool) -> ProfileResponse {
    ProfileResponse {
        profile: ProfileData {
            username: user.name.clone(),
            bio: user.bio.clone(),
            image: user.image.clone(),
            following,
        },
    }
}

#[debug_handler]
pub async fn get_profile(
    Path(username): Path<String>,
    State(ctx): State<AppContext>,
) -> Result<Response> {
    let target = load_user_by_username(&ctx, &username).await?;
    let following = false;

    format::json(make_profile(&target, following))
}

#[debug_handler]
pub async fn follow(
    Path(username): Path<String>,
    State(ctx): State<AppContext>,
    auth: auth::JWT,
) -> Result<Response> {
    let current = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;

    let target = load_user_by_username(&ctx, &username).await?;

    if current.id == target.id {
        return bad_request("Cannot follow yourself");
    }

    let already_following = is_following(&ctx, current.id, target.id).await?;
    if !already_following {
        let model = followers::ActiveModel {
            follower_id: Set(current.id),
            following_id: Set(target.id),
            created_at: Set(Some(chrono::Utc::now().into())),
        };
        model.insert(&ctx.db).await?;
    }

    format::json(make_profile(&target, true))
}

#[debug_handler]
pub async fn unfollow(
    Path(username): Path<String>,
    State(ctx): State<AppContext>,
    auth: auth::JWT,
) -> Result<Response> {
    let current = users::Model::find_by_pid(&ctx.db, &auth.claims.pid).await?;

    let target = load_user_by_username(&ctx, &username).await?;

    if current.id == target.id {
        return bad_request("Cannot unfollow yourself");
    }

    if let Some(record) = followers::Entity::find()
        .filter(
            followers::Column::FollowerId
                .eq(current.id)
                .and(followers::Column::FollowingId.eq(target.id)),
        )
        .one(&ctx.db)
        .await?
    {
        record.delete(&ctx.db).await?;
    }

    format::json(make_profile(&target, false))
}

pub fn routes() -> Routes {
    Routes::new()
        .prefix("/api/profiles")
        .add("/{username}", get(get_profile))
        .add("/{username}/follow", post(follow))
        .add("/{username}/follow", delete(unfollow))
}
