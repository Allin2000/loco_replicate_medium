use loco_rs::schema::*;
use sea_orm_migration::prelude::*;

#[derive(DeriveMigrationName)]
pub struct Migration;

#[async_trait::async_trait]
impl MigrationTrait for Migration {
    async fn up(&self, m: &SchemaManager) -> Result<(), DbErr> {
        create_table(m, "articles",
            &[
            
            ("id", ColType::PkAuto),
            
            ("slug", ColType::StringUniq),
            ("title", ColType::String),
            ("description", ColType::TextNull),
            ("body", ColType::Text),
            ("created_at", ColType::TimestampWithTimeZone),
            ("updated_at", ColType::TimestampWithTimeZoneNull),
            ],
            &[
            ("user", "author_id"),
            ]
        ).await
    }

    async fn down(&self, m: &SchemaManager) -> Result<(), DbErr> {
        drop_table(m, "articles").await
    }
}
