use loco_rs::schema::*;
use sea_orm_migration::prelude::*;
use sea_orm_migration::sea_orm::sea_query::{Table, ColumnDef, ForeignKey, ForeignKeyAction, Index, Expr};

#[derive(DeriveMigrationName)]
pub struct Migration;

#[async_trait::async_trait]
impl MigrationTrait for Migration {
    async fn up(&self, m: &SchemaManager) -> Result<(), DbErr> {
        m.create_table(
            Table::create()
                .table(Alias::new("favorites"))
                .col(ColumnDef::new(Alias::new("user_id")).integer().not_null())
                .col(ColumnDef::new(Alias::new("article_id")).integer().not_null())
                .col(ColumnDef::new(Alias::new("created_at")).timestamp_with_time_zone().default(Expr::current_timestamp()))
                .primary_key(Index::create().name("pk-favorites").col(Alias::new("user_id")).col(Alias::new("article_id")))
                .foreign_key(
                    ForeignKey::create()
                        .name("fk-favorites-user_id")
                        .from(Alias::new("favorites"), Alias::new("user_id"))
                        .to(Alias::new("users"), Alias::new("id"))
                        .on_delete(ForeignKeyAction::Cascade)
                )
                .foreign_key(
                    ForeignKey::create()
                        .name("fk-favorites-article_id")
                        .from(Alias::new("favorites"), Alias::new("article_id"))
                        .to(Alias::new("articles"), Alias::new("id"))
                        .on_delete(ForeignKeyAction::Cascade)
                )
                .to_owned(),
        )
        .await?;
        Ok(())
    }

    async fn down(&self, m: &SchemaManager) -> Result<(), DbErr> {
        drop_table(m, "favorites").await?;
        Ok(())
    }
}

