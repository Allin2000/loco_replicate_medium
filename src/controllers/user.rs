#![allow(clippy::missing_errors_doc)]
#![allow(clippy::unnecessary_struct_initialization)]
#![allow(clippy::unused_async)]
use loco_rs::prelude::*;
use serde::{Deserialize, Serialize};

use crate::controllers::auth::make_user_response;
use crate::models::_entities::users::{ActiveModel, Entity, Model};

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct UpdateUserParams {
    pub name: Option<String>,
    pub email: Option<String>,
    pub bio: Option<String>,
    pub image: Option<String>,
}

impl UpdateUserParams {
    fn apply(&self, item: &mut ActiveModel) {
        if let Some(name) = &self.name {
            item.name = Set(name.clone());
        }
        if let Some(email) = &self.email {
            item.email = Set(email.clone());
        }
        if let Some(bio) = &self.bio {
            item.bio = Set(Some(bio.clone()));
        }
        if let Some(image) = &self.image {
            item.image = Set(Some(image.clone()));
        }
    }
}

async fn load_current_user(ctx: &AppContext, auth: auth::JWT) -> Result<Model> {
    Model::find_by_pid(&ctx.db, &auth.claims.pid)
        .await
        .map_err(|err| err.into())
}

#[debug_handler]
pub async fn get_current(auth: auth::JWT, State(ctx): State<AppContext>) -> Result<Response> {
    let user = load_current_user(&ctx, auth).await?;
    let jwt_secret = ctx.config.get_jwt_config()?;
    let token = user
        .generate_jwt(&jwt_secret.secret, jwt_secret.expiration)
        .or_else(|_| unauthorized("unauthorized!"))?;
    format::json(make_user_response(&user, token))
}

#[debug_handler]
pub async fn update_current(
    auth: auth::JWT,
    State(ctx): State<AppContext>,
    Json(params): Json<UpdateUserParams>,
) -> Result<Response> {
    let current_user = load_current_user(&ctx, auth).await?;
    let mut model = current_user.into_active_model();
    params.apply(&mut model);
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
