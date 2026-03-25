#![allow(elided_lifetimes_in_paths)]
#![allow(clippy::wildcard_imports)]
pub use sea_orm_migration::prelude::*;
mod m20220101_000001_users;

mod m20260324_030433_add_columns_to_users;
mod m20260325_020548_articles;
mod m20260325_020817_comments;
mod m20260325_021005_tags;
mod m20260325_022519_article_tags;
mod m20260325_022543_followers;
mod m20260325_022600_favorites;
pub struct Migrator;

#[async_trait::async_trait]
impl MigratorTrait for Migrator {
    fn migrations() -> Vec<Box<dyn MigrationTrait>> {
        vec![
            Box::new(m20220101_000001_users::Migration),
            Box::new(m20260324_030433_add_columns_to_users::Migration),
            Box::new(m20260325_020548_articles::Migration),
            Box::new(m20260325_020817_comments::Migration),
            Box::new(m20260325_021005_tags::Migration),
            Box::new(m20260325_022519_article_tags::Migration),
            Box::new(m20260325_022543_followers::Migration),
            Box::new(m20260325_022600_favorites::Migration),
            // inject-above (do not remove this comment)
        ]
    }
}