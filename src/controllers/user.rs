// controllers/user.rs

#![allow(clippy::missing_errors_doc)]
#![allow(clippy::unnecessary_struct_initialization)]
#![allow(clippy::unused_async)]
use loco_rs::prelude::*;

use crate::controllers::auth::make_user_response;
use crate::dto::user::UpdateUserEnvelope;
use crate::models::_entities::users::Model;

async fn load_current_user(ctx: &AppContext, auth: auth::JWT) -> Result<Model> {
    Model::find_by_pid(&ctx.db, &auth.claims.pid)
        .await
        .map_err(|err| err.into())
}

/// GET /api/user — return current authenticated user.
#[debug_handler]
pub async fn get_current(auth: auth::JWT, State(ctx): State<AppContext>) -> Result<Response> {
    let user = load_current_user(&ctx, auth).await?;
    let jwt_secret = ctx.config.get_jwt_config()?;
    let token = user
        .generate_jwt(&jwt_secret.secret, jwt_secret.expiration)
        .or_else(|_| unauthorized("unauthorized!"))?;
    format::json(make_user_response(&user, token))
}

/// PUT /api/user — update current authenticated user.
///
/// Body: `{ "user": { "username": "...", "email": "...", "bio": "...", "image": "..." } }`
/// All fields optional. `null` or `""` for `bio`/`image` clears the field.
#[debug_handler]
pub async fn update_current(
    auth: auth::JWT,
    State(ctx): State<AppContext>,
    Json(envelope): Json<UpdateUserEnvelope>,
) -> Result<Response> {
    let current_user = load_current_user(&ctx, auth).await?;
    let mut model = current_user.into_active_model();
    envelope.user.apply(&mut model);
    let updated = model.update(&ctx.db).await?;
    let jwt_secret = ctx.config.get_jwt_config()?;
    let token = updated
        .generate_jwt(&jwt_secret.secret, jwt_secret.expiration)
        .or_else(|_| unauthorized("unauthorized!"))?;
    format::json(make_user_response(&updated, token))
}

pub fn routes() -> Routes {
    Routes::new()
        .prefix("/api/user")
        .add("/", get(get_current))
        .add("/", put(update_current))
}