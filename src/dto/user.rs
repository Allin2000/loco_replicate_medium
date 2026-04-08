use loco_rs::prelude::*;
use sea_orm::ActiveValue::Set;
use serde::{Deserialize, Serialize};

use crate::models::_entities::users::ActiveModel;

/// Single field that can be explicitly `null`, an empty string, or a real value.
/// `Option<Option<String>>`:
///   - `None`          → field absent from JSON → don't touch the column
///   - `Some(None)`    → `null` in JSON         → clear the column (set to NULL)
///   - `Some(Some(s))` → string in JSON         → set; empty string normalizes to NULL
#[derive(Clone, Debug, Serialize)]
pub struct NullableField(Option<Option<String>>);

impl<'de> serde::Deserialize<'de> for NullableField {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        // Deserialize as Option<Option<String>> directly.
        // serde handles `"field": null`  → Some(None)
        //                `"field": "v"`  → Some(Some("v"))
        // absent fields never reach here → None is set by the outer struct's
        // `#[serde(default)]`.
        let inner: Option<String> = Option::deserialize(d)?;
        Ok(NullableField(Some(inner)))
    }
}

impl Default for NullableField {
    fn default() -> Self {
        NullableField(None) // absent → do nothing
    }
}

impl NullableField {
    /// Returns:
    ///   `None`         → absent, skip
    ///   `Some(None)`   → set column to NULL
    ///   `Some(Some(s))`→ set column to s (empty string → NULL)
    pub fn resolved(&self) -> Option<Option<String>> {
        match &self.0 {
            None => None,
            Some(None) => Some(None),
            Some(Some(s)) if s.is_empty() => Some(None),
            Some(Some(s)) => Some(Some(s.clone())),
        }
    }
}

/// Update-user request body (fields are all optional).
/// JSON shape expected: `{ "user": { "username": "...", "bio": null, ... } }`
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct UpdateUserRequest {
    #[serde(rename = "username")]
    pub name: Option<String>,
    pub email: Option<String>,
    #[serde(default)]
    pub bio: NullableField,
    #[serde(default)]
    pub image: NullableField,
}

impl UpdateUserRequest {
    /// Apply non-absent fields onto the SeaORM active model.
    pub fn apply(&self, item: &mut ActiveModel) {
        if let Some(name) = &self.name {
            item.name = Set(name.clone());
        }
        if let Some(email) = &self.email {
            item.email = Set(email.clone());
        }
        if let Some(resolved) = self.bio.resolved() {
            item.bio = Set(resolved);
        }
        if let Some(resolved) = self.image.resolved() {
            item.image = Set(resolved);
        }
    }
}

/// Envelope for update requests: `{ "user": <UpdateUserRequest> }`
#[derive(Clone, Debug, Deserialize)]
pub struct UpdateUserEnvelope {
    pub user: UpdateUserRequest,
}