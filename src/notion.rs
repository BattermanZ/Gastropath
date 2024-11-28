use reqwest::Client;
use serde_json::{json, Value};
use std::env;
use log::{info, error, debug};
use crate::RestaurantDetails;

pub async fn create_or_update_entry(
    client: &Client,
    details: RestaurantDetails,
    cover_url: Option<String>,
) -> Result<String, String> {
    info!("Creating or updating Notion entry for: {}", details.name);
    let api_key = env::var("NOTION_API_KEY").map_err(|e| e.to_string())?;
    let database_id = env::var("NOTION_DATABASE_ID").map_err(|e| e.to_string())?;

    let existing_entry = find_existing_entry(client, &api_key, &database_id, &details.name).await?;

    if existing_entry.is_some() {
        return Ok("Restaurant already in the database".to_string());
    }

    let url = "https://api.notion.com/v1/pages".to_string();

    debug!("Notion API request URL: {}", url);

    let mut data = json!({
        "parent": { "database_id": database_id },
        "properties": {
            "City": {
                "rich_text": [{"text": {"content": details.city}}]
            },
            "Country": {
                "rich_text": [{"text": {"content": details.country}}]
            },
            "Cuisine Type": {
                "rich_text": [{"text": {"content": details.cuisine_type}}]
            },
            "Google Maps": {
                "url": details.google_maps_link
            },
            "Price range": {
                "select": {"name": details.price_level}
            },
            "Website": {
                "url": details.website
            },
            "Name": {
                "title": [{"text": {"content": details.name}}]
            }
        },
        "icon": {"type": "emoji", "emoji": "🍽️"}
    });

    if let Some(url) = cover_url {
        data["cover"] = json!({"type": "external", "external": {"url": url}});
    }

    debug!("Notion API request data: {:?}", data);

    let response = client.post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Notion-Version", "2022-06-28")
        .json(&data)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    if response.status().is_success() {
        Ok("Restaurant successfully added to Gastropath".to_string())
    } else {
        let status = response.status();
        let error_body = response.text().await.map_err(|e| e.to_string())?;
        error!("Failed to create Notion entry. Status: {}, Body: {}", status, error_body);
        Err("Failed to add restaurant to Gastropath".to_string())
    }
}

async fn find_existing_entry(
    client: &Client,
    api_key: &str,
    database_id: &str,
    restaurant_name: &str,
) -> Result<Option<String>, String> {
    let url = format!("https://api.notion.com/v1/databases/{}/query", database_id);
    debug!("Querying Notion database: {}", url);

    let query = json!({
        "filter": {
            "property": "Name",
            "title": {
                "equals": restaurant_name
            }
        }
    });

    let response = client.post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Notion-Version", "2022-06-28")
        .json(&query)
        .send()
        .await
        .map_err(|e| e.to_string())?
        .json::<Value>()
        .await
        .map_err(|e| e.to_string())?;

    debug!("Notion query response: {:?}", response);

    if let Some(results) = response["results"].as_array() {
        if let Some(first_result) = results.first() {
            return Ok(first_result["id"].as_str().map(String::from));
        }
    }

    Ok(None)
}

