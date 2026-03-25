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
                .table(Alias::new("article_tags"))
                .col(ColumnDef::new(Alias::new("article_id")).integer().not_null())
                .col(ColumnDef::new(Alias::new("tag_id")).integer().not_null())
                .col(ColumnDef::new(Alias::new("created_at")).timestamp_with_time_zone().default(Expr::current_timestamp()))
                .primary_key(Index::create().name("pk-article_tags").col(Alias::new("article_id")).col(Alias::new("tag_id")))
                .foreign_key(
                    ForeignKey::create()
                        .name("fk-article_tags-article_id")
                        .from(Alias::new("article_tags"), Alias::new("article_id"))
                        .to(Alias::new("articles"), Alias::new("id"))
                        .on_delete(ForeignKeyAction::Cascade)
                )
                .foreign_key(
                    ForeignKey::create()
                        .name("fk-article_tags-tag_id")
                        .from(Alias::new("article_tags"), Alias::new("tag_id"))
                        .to(Alias::new("tags"), Alias::new("id"))
                        .on_delete(ForeignKeyAction::Cascade)
                )
                .to_owned(),
        )
        .await?;
        Ok(())
    }

    async fn down(&self, m: &SchemaManager) -> Result<(), DbErr> {
        drop_table(m, "article_tags").await?;
        Ok(())
    }
}

