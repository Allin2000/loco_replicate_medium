// dto/article.rs

use loco_rs::prelude::*;
use sea_orm::ActiveValue::Set;
use serde::{Deserialize, Serialize};

use crate::models::_entities::articles::ActiveModel;

// ---------------------------------------------------------------------------
// TagList field — distinguishes absent / null / [] / [...]
//
// Option<Option<Vec<String>>>:
//   None              -> absent from JSON -> preserve existing tags
//   Some(None)        -> `null` in JSON   -> REJECT with 422
//   Some(Some(vec))   -> array            -> replace tags (may be empty)
// ---------------------------------------------------------------------------
#[derive(Clone, Debug, Serialize)]
pub struct TagListField(Option<Option<Vec<String>>>);

impl<'de> serde::Deserialize<'de> for TagListField {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let inner: Option<Vec<String>> = Option::deserialize(d)?;
        Ok(TagListField(Some(inner)))
    }
}

impl Default for TagListField {
    fn default() -> Self {
        TagListField(None)
    }
}

pub enum TagListIntent {
    Preserve,
    Null,
    Replace(Vec<String>),
}

impl TagListField {
    pub fn intent(&self) -> TagListIntent {
        match &self.0 {
            None => TagListIntent::Preserve,
            Some(None) => TagListIntent::Null,
            Some(Some(v)) => TagListIntent::Replace(v.clone()),
        }
    }
}

// ---------------------------------------------------------------------------
// Create request DTO
// ---------------------------------------------------------------------------
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct CreateArticleRequest {
    pub title: String,
    pub description: String,
    pub body: String,
    #[serde(rename = "tagList", default)]
    pub tag_list: Vec<String>,
}

// ---------------------------------------------------------------------------
// Update request DTO
// ---------------------------------------------------------------------------
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct UpdateArticleRequest {
    pub title: Option<String>,
    pub description: Option<String>,
    pub body: Option<String>,
    #[serde(rename = "tagList", default)]
    pub tag_list: TagListField,
}

impl UpdateArticleRequest {
    pub fn apply_scalars(&self, item: &mut ActiveModel) {
        if let Some(title) = &self.title {
            item.slug = Set(title.to_lowercase().replace(' ', "-").replace(['.', ','], ""));
            item.title = Set(title.clone());
        }
        if let Some(description) = &self.description {
            item.description = Set(Some(description.clone()));
        }
        if let Some(body) = &self.body {
            item.body = Set(body.clone());
        }
    }
}

// ---------------------------------------------------------------------------
// Envelopes
// ---------------------------------------------------------------------------
#[derive(Debug, Deserialize)]
pub struct CreateArticleEnvelope {
    pub article: CreateArticleRequest,
}

#[derive(Debug, Deserialize)]
pub struct UpdateArticleEnvelope {
    pub article: UpdateArticleRequest,
}

// ---------------------------------------------------------------------------
// Query params for GET /api/articles and /api/articles/feed
// ---------------------------------------------------------------------------
#[derive(Debug, Deserialize, Default)]
pub struct ArticleListQuery {
    pub tag: Option<String>,
    pub author: Option<String>,
    pub favorited: Option<String>,
    /// Maximum number of articles to return
    pub limit: Option<u64>,
    /// Number of articles to skip
    pub offset: Option<u64>,
}