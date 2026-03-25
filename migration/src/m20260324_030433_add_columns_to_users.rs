use loco_rs::schema::*;
use sea_orm_migration::prelude::*;

#[derive(DeriveMigrationName)]
pub struct Migration;

#[async_trait::async_trait]
impl MigrationTrait for Migration {
    async fn up(&self, m: &SchemaManager) -> Result<(), DbErr> {
        add_column(m, "users", "bio", ColType::TextNull).await?;
        add_column(m, "users", "image", ColType::StringNull).await?;
        Ok(())
    }

    async fn down(&self, m: &SchemaManager) -> Result<(), DbErr> {
        remove_column(m, "users", "bio").await?;
        remove_column(m, "users", "image").await?;
        Ok(())
    }
}
