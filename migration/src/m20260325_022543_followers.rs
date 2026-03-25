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
                .table(Alias::new("followers"))
                .col(ColumnDef::new(Alias::new("follower_id")).integer().not_null())
                .col(ColumnDef::new(Alias::new("following_id")).integer().not_null())
                .col(ColumnDef::new(Alias::new("created_at")).timestamp_with_time_zone().default(Expr::current_timestamp()))
                .primary_key(Index::create().name("pk-followers").col(Alias::new("follower_id")).col(Alias::new("following_id")))
                .foreign_key(
                    ForeignKey::create()
                        .name("fk-followers-follower_id")
                        .from(Alias::new("followers"), Alias::new("follower_id"))
                        .to(Alias::new("users"), Alias::new("id"))
                        .on_delete(ForeignKeyAction::Cascade)
                )
                .foreign_key(
                    ForeignKey::create()
                        .name("fk-followers-following_id")
                        .from(Alias::new("followers"), Alias::new("following_id"))
                        .to(Alias::new("users"), Alias::new("id"))
                        .on_delete(ForeignKeyAction::Cascade)
                )
                .to_owned(),
        )
        .await?;
        Ok(())
    }

    async fn down(&self, m: &SchemaManager) -> Result<(), DbErr> {
        drop_table(m, "followers").await?;
        Ok(())
    }
}

